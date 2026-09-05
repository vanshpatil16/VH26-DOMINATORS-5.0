"""Scalpel CFG wrapper — bug fixes + helpers.

Scalpel provides the CFG; we patch two bugs discovered in Phase 1/2:
 1. visit_Try crashes when finalbody==[] (UnboundLocalError: finally_block)
 2. visit_Return leaves phantom empty block that pollutes predecessors

We do NOT fork Scalpel — we monkey-patch at import time and expose helpers.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Locate Scalpel: prefer pip-installed; else find local checkout in known spots.
def _ensure_scalpel_importable() -> None:
    try:
        import scalpel  # noqa: F401
        return
    except ImportError:
        pass
    here = Path(__file__).resolve().parents[1]
    candidates = [
        here / "Scalpel" / "src",
        here / "frontend" / "Scalpel" / "src",
        here / "Scalpel",
        here / "frontend" / "Scalpel",
    ]
    for cand in candidates:
        if (cand / "scalpel").is_dir():
            sys.path.insert(0, str(cand))
            return
    raise ImportError(
        "Scalpel not found. Install it: pip install python-scalpel "
        "(or place a checkout at ./Scalpel/src)"
    )


_ensure_scalpel_importable()

from scalpel.cfg.builder import CFGBuilder, merge_exitcases  # noqa: E402
from scalpel.cfg.model import Block, CFG  # noqa: E402

_PATCHED = False


def _patched_clean_cfg(self, block: "Block", visited: list):
    """Fixed clean_cfg — keeps genuine terminal exits, drops dead code.

    Scalpel's original removes empty tail blocks (function falling off the end
    after an `if`), which DELETES the fall-through path. That made `def h(f):
    if x: f.close()` look like it always closes. Fix: an empty block with no
    exits but with predecessors is a genuine function exit — keep it.

    ALSO: blocks created after `return`/`raise` are DEAD (unreachable). They
    must never be merged into the surrounding CFG — otherwise a `return` inside
    an except handler appears to fall through to the after-try block, hiding
    real leaks. Dead blocks are tracked via _dead_block_ids.
    """
    if block.id in visited:
        return
    visited.append(block.id)

    # Dead code after return/raise: sever entirely, never merge.
    if getattr(self, "_dead_block_ids", None) and block.id in self._dead_block_ids:
        for pred in list(block.predecessors):
            if pred in pred.source.exits:
                pred.source.exits.remove(pred)
        block.predecessors = []
        block.exits = []
        return

    if block.is_empty() and not block.exits and block.predecessors:
        # terminal exit node: fall off the end of the function. Keep it.
        if block not in self.cfg.finalblocks:
            self.cfg.finalblocks.append(block)
        for pred in list(block.predecessors):
            self.clean_cfg(pred.source, visited)
        return

    # Original Scalpel logic for middle empty blocks (merge around them).
    if block.is_empty():
        for pred in block.predecessors:
            for exit in block.exits:
                self.add_exit(
                    pred.source,
                    exit.target,
                    merge_exitcases(pred.exitcase, exit.exitcase),
                )
                if exit in exit.target.predecessors:
                    exit.target.predecessors.remove(exit)
            if pred in pred.source.exits:
                pred.source.exits.remove(pred)
        block.predecessors = []
        for exit in block.exits[:]:
            self.clean_cfg(exit.target, visited)
        block.exits = []
    else:
        for exit in block.exits[:]:
            self.clean_cfg(exit.target, visited)


def _patched_visit_Try(self, node: ast.Try):
    """Fixed visit_Try — handles missing finally_block gracefully."""
    # Add the try statement at the end of the current block.
    self.add_statement(self.current_block, node)

    after_try_block = self.new_block()
    final_block = self.new_block()
    self.add_exit(final_block, after_try_block)

    try_block = self.new_block()
    self.add_exit(self.current_block, try_block, ast.Constant(value=True))

    else_block_for_link = self.new_block()
    self.add_exit(try_block, else_block_for_link, ast.Constant(value=True))
    self.add_exit(else_block_for_link, final_block)

    n_handlers = len(node.handlers)
    handler_blocks = [self.new_block() for _ in range(n_handlers)]
    for hb in handler_blocks:
        self.add_exit(self.current_block, hb)
        # NOTE: do NOT pre-link hb -> final_block here. A handler that ends in
        # return/raise must not fall through to the after-try/finally code.
        # The fall-through edge is added after visiting, only if the handler
        # did not terminate (see the guarded add_exit below).

    # second set (original code duplicated this — keep behavior but fix bug)
    after_try_block2 = self.new_block()
    # keep after_try_block as the real after-try; use second only if needed
    after_handlers_and_else = after_try_block

    # FIX: only create finally_block if finalbody exists; else use final_block
    if len(node.finalbody) > 0:
        finally_block = self.new_block()
        after_handlers_and_else = finally_block
    else:
        finally_block = final_block  # no finally body -> point to final_block
        after_handlers_and_else = after_try_block

    self.current_block = try_block
    for child in node.body:
        self.visit(child)

    else_block = self.new_block()
    self.add_exit(self.current_block, else_block)
    self.current_block = else_block
    for child in node.orelse:
        self.visit(child)
    self.add_exit(self.current_block, after_handlers_and_else)

    for i in range(n_handlers):
        self.current_block = handler_blocks[i]
        self.visit(node.handlers[i])
        # Fall through to final_block ONLY if the handler did not terminate
        # (return/raise). A dead current block means the handler returned/raised.
        if not self.current_block.exits and not (
            hasattr(self, "_dead_block_ids") and self.current_block.id in self._dead_block_ids
        ):
            self.add_exit(self.current_block, final_block)

    # FIX: guard for when there is no finally
    if len(node.finalbody) > 0:
        self.current_block = finally_block
        for child in node.finalbody:
            self.visit(child)
        self.add_exit(self.current_block, after_try_block)

    self.current_block = final_block
    for child in node.finalbody:
        self.visit(child)
    if not self.current_block.exits:
        self.add_exit(self.current_block, after_try_block)

    self.current_block = after_try_block


def _patched_visit_Return(self, node: ast.Return):
    self.add_statement(self.current_block, node)
    self.cfg.finalblocks.append(self.current_block)
    # New block after return is DEAD code: statements after it are unreachable.
    # Track it so clean_cfg severs it instead of merging it back into the graph
    # (otherwise a `return` in an except handler looks like it falls through
    # to the after-try block, hiding real leaks).
    if not hasattr(self, "_dead_block_ids"):
        self._dead_block_ids = set()
    new_block = self.new_block()
    self._dead_block_ids.add(new_block.id)
    self.current_block = new_block


def _patched_visit_Raise(self, node: ast.Raise):
    self.add_statement(self.current_block, node)
    self.cfg.finalblocks.append(self.current_block)
    if not hasattr(self, "_dead_block_ids"):
        self._dead_block_ids = set()
    new_block = self.new_block()
    self._dead_block_ids.add(new_block.id)
    self.current_block = new_block


def apply_patches() -> None:
    global _PATCHED
    if _PATCHED:
        return
    CFGBuilder.visit_Try = _patched_visit_Try
    CFGBuilder.visit_Return = _patched_visit_Return
    CFGBuilder.visit_Raise = _patched_visit_Raise
    CFGBuilder.clean_cfg = _patched_clean_cfg
    _PATCHED = True


# Apply on import
apply_patches()


def _edge_key(exitcase) -> tuple:
    """Normalize an edge's exitcase for dedupe: Constant(True) == fall-through."""
    if exitcase is None:
        return ("none", None)
    if isinstance(exitcase, ast.Constant) and exitcase.value is True:
        return ("none", None)  # True-guard edge == fall-through for dedupe purposes
    return ("expr", ast.dump(exitcase))


def dedupe_cfg(cfg: CFG) -> CFG:
    """Remove duplicate/self edges left by clean_cfg's block merging.

    Scalpel's clean_cfg can produce:
      - duplicate exits with identical (target, exitcase)
      - Constant(True)-guarded edges AND plain fall-through edges to the
        same target (from the try/finally machinery) — semantically duplicates
      - duplicate predecessors pointing at the same phantom merge
    Duplicate edges break DFS path enumeration (double-counting paths).
    """
    for block in cfg.get_all_blocks():
        # Dedupe exits
        seen: set = set()
        new_exits = []
        for e in block.exits:
            key = (e.target.id, _edge_key(e.exitcase))
            if key in seen:
                # remove twin from target's predecessors
                if e in e.target.predecessors:
                    e.target.predecessors.remove(e)
                continue
            seen.add(key)
            new_exits.append(e)
        block.exits = new_exits
        # Dedupe predecessors
        seen = set()
        new_preds = []
        for p in block.predecessors:
            key = (p.source.id, _edge_key(p.exitcase))
            if key in seen:
                continue
            seen.add(key)
            new_preds.append(p)
        block.predecessors = new_preds
    # Recurse into nested function/class CFGs (they are separate CFG objects)
    for sub_cfg in cfg.functioncfgs.values():
        dedupe_cfg(sub_cfg)
    for cls_cfg in cfg.class_cfgs.values():
        dedupe_cfg(cls_cfg)
    return cfg


def build_cfg(src: str, name: str = "module", desugar_match: bool = True) -> CFG:
    """Build CFG from source using patched builder.

    - Desugars match statements (Scalpel has no visit_Match — bodies get swallowed)
    - Dedupes CFG edges produced by clean_cfg
    """
    from .desugar import desugar_module

    tree = ast.parse(src)
    if desugar_match:
        tree = desugar_module(tree)
    builder = CFGBuilder()
    cfg = builder.build(name, tree)
    return dedupe_cfg(cfg)


def build_cfg_from_file(path: str | Path, name: str | None = None) -> CFG:
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    return build_cfg(src, name or p.stem)


def get_function_cfgs(cfg: CFG) -> dict[tuple[int, str], CFG]:
    """Return dict of (block_id, name) -> function CFG."""
    return dict(cfg.functioncfgs)


def get_all_blocks_filtered(cfg: CFG) -> list[Block]:
    """BFS blocks but filtered: drop phantom empty blocks with no stmts."""
    raw = cfg.get_all_blocks()
    # Filter: empty and not entry and has predecessors that are finals is suspicious
    # For safety, keep entryblock even if empty; drop others that are empty and have no meaningful stmts
    filtered = [b for b in raw if not (b.is_empty() and b is not cfg.entryblock)]
    return filtered


def iter_cfg_blocks(cfg: CFG):
    """Iterate blocks in BFS order, filtered."""
    yield from get_all_blocks_filtered(cfg)
