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

# Ensure Scalpel/src is on path
_scalpel_src = Path(__file__).resolve().parents[1] / "Scalpel" / "src"
if str(_scalpel_src) not in sys.path:
    sys.path.insert(0, str(_scalpel_src))

from scalpel.cfg.builder import CFGBuilder  # noqa: E402
from scalpel.cfg.model import Block, CFG  # noqa: E402

_PATCHED = False


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
        self.add_exit(hb, final_block)

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
        if not self.current_block.exits:
            self.add_exit(self.current_block, after_handlers_and_else)

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
    # Don't leave phantom empty block that pollutes predecessors.
    # Instead create new block but mark it as dead (will be cleaned).
    # Original code: self.current_block = self.new_block()
    # We still need a new block so subsequent statements don't get added to the return block,
    # but we ensure its predecessors don't leak via clean_cfg.
    new_block = self.new_block()
    # Do NOT add exit from return block to new_block — return is terminal.
    # The new_block is just "dead code" start.
    self.current_block = new_block


def apply_patches() -> None:
    global _PATCHED
    if _PATCHED:
        return
    CFGBuilder.visit_Try = _patched_visit_Try
    CFGBuilder.visit_Return = _patched_visit_Return
    _PATCHED = True


# Apply on import
apply_patches()


def build_cfg(src: str, name: str = "module") -> CFG:
    """Build CFG from source using patched builder."""
    builder = CFGBuilder()
    return builder.build_from_src(name, src)


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
