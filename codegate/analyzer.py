"""CodeGate analyzer — path-sensitive resource-leak detection on Scalpel CFG."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import CodeGateConfig, ResourceSpec
from .imports import build_import_map, resolve_call_name
from .scalpel_patch import build_cfg, get_all_blocks_filtered


@dataclass
class Leak:
    file: str
    func: str
    line: int
    col: int
    var: str
    acquire: str
    release: str
    message: str
    # Evidence
    acquire_line: int
    # "path" = normal control-flow leak; "exception" = may-throw call can leak
    kind: str = "path"
    paths: list[list[int]] = field(default_factory=list)  # block id paths that leak
    safe_paths: list[list[int]] = field(default_factory=list)
    # Human-readable path summaries (statement sources along each path)
    path_sources: list[list[str]] = field(default_factory=list)
    safe_path_sources: list[list[str]] = field(default_factory=list)
    # Short exception-risk explanation (rendered separately from message)
    exception_note: str = ""

    def to_dict(self):
        return {
            "file": self.file,
            "func": self.func,
            "line": self.line,
            "col": self.col,
            "var": self.var,
            "acquire": self.acquire,
            "release": self.release,
            "message": self.message,
            "acquire_line": self.acquire_line,
            "kind": self.kind,
            "leaking_paths": self.paths,
            "safe_paths": self.safe_paths,
            "exception_note": self.exception_note,
        }


# ---------------------------------------------------------------------------
# Helpers to classify AST nodes
# ---------------------------------------------------------------------------

def _call_name(node: ast.Call) -> Optional[str]:
    """Return dotted name for Call.func, e.g., socket.socket, open."""
    func = node.func
    parts: list[str] = []
    cur = func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(cur, ast.Subscript):
        # e.g., foo()[0].bar() -> ignore
        return None
    return None


def _is_with_acquire(stmt: ast.With, resources: list[ResourceSpec], import_map: dict[str, str] | None = None) -> bool:
    """With(items=[withitem(context_expr=Call)]) — if that Call matches a tracked
    resource, or is contextlib.closing(...) (which releases anything on exit), it's safe."""
    for item in stmt.items:
        expr = item.context_expr
        if isinstance(expr, ast.Call):
            name = _call_name(expr)
            if not name:
                continue
            resolved = resolve_call_name(name, import_map)
            if any(r.matches_acquire(resolved) for r in resources):
                return True
            # contextlib.closing(obj) releases obj.__exit__ at with-exit
            if resolved == "contextlib.closing" or resolved.endswith(".closing"):
                return True
    return False


def _get_acquire_info(
    stmt: ast.AST,
    resources: list[ResourceSpec],
    import_map: dict[str, str] | None = None,
) -> Optional[tuple[str, str, str]]:
    """
    If stmt is   var = <acquire>(...)   matching resources, return (var, canonical_acquire, release).
    Canonical name is import-resolved (e.g. db.connect -> sqlite3.connect).
    Returns None otherwise.
    """
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        var = stmt.targets[0].id
        if isinstance(stmt.value, ast.Call):
            name = _call_name(stmt.value)
            if name:
                resolved = resolve_call_name(name, import_map)
                for r in resources:
                    if r.matches_acquire(resolved):
                        return (var, resolved, r.release)
    # also AnnAssign  x: t = open()
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Call):
        var = stmt.target.id
        name = _call_name(stmt.value)
        if name:
            resolved = resolve_call_name(name, import_map)
            for r in resources:
                if r.matches_acquire(resolved):
                    return (var, resolved, r.release)
    return None


def _is_release(stmt: ast.AST, aliases: set[str], spec: ResourceSpec | None = None,
                release_name: str = "close") -> Optional[str]:
    """
    If stmt is   <alias>.release(...)   where alias in aliases, return alias name.
    Checks the primary release name plus alt_releases (e.g. Popen.wait/kill).
    """
    method = None
    call = None
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute):
            method = call.func.attr
    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await) \
            and isinstance(stmt.value.value, ast.Call) \
            and isinstance(stmt.value.value.func, ast.Attribute):
        # await httpx_client.aclose()
        call = stmt.value.value
        method = call.func.attr  # type: ignore[union-attr]
    if method is None or call is None:
        return None
    valid = [release_name]
    if spec is not None:
        valid += spec.alt_releases
    if method in valid and isinstance(call.func.value, ast.Name) and call.func.value.id in aliases:
        return call.func.value.id
    return None


def _is_with_block_safe(block, resources: list[ResourceSpec]) -> bool:
    """If block's first stmt is a With that acquires a tracked resource, whole with is safe by desugaring."""
    for stmt in block.statements:
        if isinstance(stmt, ast.With) and _is_with_acquire(stmt, resources):
            return True
    return False


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def _find_aliases_for_resource(all_blocks, resource_var: str, resource_res_id: int, aliases_state: dict[str, int]) -> set[str]:
    """Computed dynamically during DFS; this helper is not used directly anymore."""
    # Kept for compatibility
    return set()


def analyze_function_cfg(fcfg, func_name: str, file_path: str, config: CodeGateConfig,
                         import_map: dict[str, str] | None = None) -> list[Leak]:
    """Analyze a single function CFG, return leaks."""
    resources = config.resources
    blocks = get_all_blocks_filtered(fcfg)
    if not blocks:
        return []

    id2block = {b.id: b for b in blocks}
    entry = fcfg.entryblock
    # In case entry was filtered (empty), find smallest id block with no preds that survived
    if entry not in blocks:
        # fallback to first block in iteration
        entry = blocks[0] if blocks else None
        if entry is None:
            return []

    leaks: list[Leak] = []

    # We need to track per-resource. For MVP, assume one resource type at a time but
    # we handle multiple acquires by live-set keyed by resource id (lineno of acquire).
    # Each resource id maps to (var, acquire_name, release, aliases set)
    # But we simplify: live = dict var -> res_id, and res_info = dict res_id -> (var, acquire, release)
    # Alias tracking: alias dict maps variable -> res_id. Multiple vars can point to same res_id.

    # Enumerate all acquires first to know which lines are acquires (for quick check)
    # But we do stateful DFS that discovers them on the fly.

    # DFS with state copying: live: dict[var -> res_id], res_info: dict[res_id -> (orig_var, acquire, release)]
    # visited: set[block_id] to avoid infinite loops (loops visited once — sound for "exists leak" since loop can be 0 iterations)

    found_leaks: dict[int, Leak] = {}  # res_id -> Leak (first evidence)

    # Track paths per res_id: leaking paths vs safe paths
    path_evidence: dict[int, dict] = {}  # res_id -> {"leaking": [], "safe": []}

    def _process_block(block, live: dict[str, int], res_info: dict[int, tuple[str, str, str]], path: list[int]):
        """Simulate block statements sequentially, updating live/res_info. Returns (new_live, new_res_info, leaks_inside, new_path)"""
        new_live = dict(live)
        new_res = dict(res_info)
        local_leaks: list[int] = []  # res_ids leaked inside this block

        for stmt in block.statements:
            # `with <tracked-resource>(...) as h:` — context-managed, no live entry.
            if isinstance(stmt, ast.With) and config.with_is_safe and _is_with_acquire(stmt, resources, import_map):
                # Also: `with contextlib.closing(f):` releases an earlier-acquired `f`
                for item in stmt.items:
                    expr = item.context_expr
                    if isinstance(expr, ast.Call):
                        cname = resolve_call_name(_call_name(expr) or "", import_map)
                        if cname == "contextlib.closing" or cname.endswith(".closing"):
                            for a in expr.args:
                                if isinstance(a, ast.Name) and a.id in new_live:
                                    closed_res = new_live[a.id]
                                    vars_to_remove = [v for v, r in list(new_live.items()) if r == closed_res]
                                    for v in vars_to_remove:
                                        del new_live[v]
                # Skip — this resource is context-managed
                continue
            # `h = es.enter_context(<acquire>())` (ExitStack) — managed, skip live creation
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                vname = resolve_call_name(_call_name(stmt.value) or "", import_map)
                if vname.endswith(".enter_context") or vname == "contextlib.ExitStack.enter_context":
                    continue

            # 1) Try to detect acquire: var = acquire(...)
            acq = _get_acquire_info(stmt, resources, import_map)
            if acq:
                var, acq_name, rel_name = acq
                # If var already maps to a different live resource, that previous resource is leaked (overwritten before close)
                if var in new_live:
                    prev_res = new_live[var]
                    # Is there another alias still holding prev_res? If so, not leaked yet (still reachable)
                    other_holders = [v for v, r in new_live.items() if r == prev_res and v != var]
                    if not other_holders:
                        # leak previous
                        local_leaks.append(prev_res)
                        # mark path evidence will be handled at block level
                        if prev_res not in found_leaks:
                            orig_var, acq_n, rel_n = new_res[prev_res]
                            col = stmt.col_offset if hasattr(stmt, "col_offset") else 0
                            found_leaks[prev_res] = Leak(
                                file=file_path,
                                func=func_name,
                                line=stmt.lineno,
                                col=col,
                                var=orig_var,
                                acquire=acq_n,
                                release=rel_n,
                                message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: overwritten by '{var} = {acq_name}(...)' at line {stmt.lineno} before release",
                                acquire_line=prev_res,
                            )
                            path_evidence.setdefault(prev_res, {"leaking": [], "safe": []})
                        path_evidence[prev_res]["leaking"].append(list(path) + [block.id])
                    # Remove prev mapping from live (or keep if alias holds? already checked)
                    # Remove only this var's entry; other holders keep res alive via their keys
                    # But we will also remove res_info if no holders left
                    # First remove this var's old mapping (will be overwritten)
                    # And if no holders left, also clean res_info (but keep leak record)
                    if not other_holders:
                        # remove res from res_info? keep for reporting but mark leaked
                        # We'll keep it but remove from live set's res entry tracking
                        pass
                    # Remove old live entry for this var
                    if var in new_live:
                        del new_live[var]
                    # If no other holder, also remove from new_res? No, keep for message.

                # Create new resource id = lineno of this acquire (unique enough per function)
                res_id = stmt.lineno
                # Edge: if same lineno already used (two acquires same line?), make unique
                # Use (lineno, counter)
                orig_res_id = res_id
                counter = 0
                while res_id in new_res:
                    counter += 1
                    res_id = orig_res_id * 1000 + counter
                new_live[var] = res_id
                new_res[res_id] = (var, acq_name, rel_name)
                # Also ensure leaking entry exists for future path analysis
                path_evidence.setdefault(res_id, {"leaking": [], "safe": []})
                continue

            # 2) Alias:  y = x   where x is resource handle
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                lhs = stmt.targets[0].id
                rhs = stmt.value
                if isinstance(rhs, ast.Name):
                    rhs_var = rhs.id
                    if rhs_var in new_live:
                        res_id = new_live[rhs_var]
                        # If lhs already held different resource, leak previous (like acquire case)
                        if lhs in new_live and new_live[lhs] != res_id:
                            prev_res = new_live[lhs]
                            other_holders = [v for v, r in new_live.items() if r == prev_res and v != lhs]
                            if not other_holders:
                                local_leaks.append(prev_res)
                                if prev_res not in found_leaks:
                                    orig_var, acq_n, rel_n = new_res[prev_res]
                                    col = stmt.col_offset if hasattr(stmt, "col_offset") else 0
                                    found_leaks[prev_res] = Leak(
                                        file=file_path, func=func_name, line=stmt.lineno, col=col,
                                        var=orig_var, acquire=acq_n, release=rel_n,
                                        message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: alias '{lhs}' overwritten",
                                        acquire_line=prev_res,
                                    )
                                    path_evidence.setdefault(prev_res, {"leaking": [], "safe": []})
                                path_evidence[prev_res]["leaking"].append(list(path)+[block.id])
                        # Create alias link
                        new_live[lhs] = res_id
                        # res_info already has it
                        continue
                    else:
                        # rhs not a resource handle; if lhs was resource, it's killed -> leak unless another alias holds
                        if lhs in new_live:
                            prev_res = new_live[lhs]
                            other_holders = [v for v, r in new_live.items() if r == prev_res and v != lhs]
                            if not other_holders:
                                local_leaks.append(prev_res)
                                if prev_res not in found_leaks:
                                    orig_var, acq_n, rel_n = new_res[prev_res]
                                    col = stmt.col_offset if hasattr(stmt, "col_offset") else 0
                                    found_leaks[prev_res] = Leak(
                                        file=file_path, func=func_name, line=stmt.lineno, col=col,
                                        var=orig_var, acquire=acq_n, release=rel_n,
                                        message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: handle '{lhs}' overwritten by non-resource at line {stmt.lineno}",
                                        acquire_line=prev_res,
                                    )
                                    path_evidence.setdefault(prev_res, {"leaking": [], "safe": []})
                                path_evidence[prev_res]["leaking"].append(list(path)+[block.id])
                            del new_live[lhs]
                            # keep new_res for reporting
                        # If rhs not resource and lhs not resource, no-op
                        continue
                # RHS is not Name -> this is "lhs = <non-name>" where lhs was resource; kill if no other alias holds
                else:
                    if lhs in new_live:
                        prev_res = new_live[lhs]
                        other_holders = [v for v, r in new_live.items() if r == prev_res and v != lhs]
                        if not other_holders:
                            local_leaks.append(prev_res)
                            if prev_res not in found_leaks:
                                orig_var, acq_n, rel_n = new_res[prev_res]
                                col = stmt.col_offset if hasattr(stmt, "col_offset") else 0
                                found_leaks[prev_res] = Leak(
                                    file=file_path, func=func_name, line=stmt.lineno, col=col,
                                    var=orig_var, acquire=acq_n, release=rel_n,
                                    message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: overwritten at line {stmt.lineno}",
                                    acquire_line=prev_res,
                                )
                                path_evidence.setdefault(prev_res, {"leaking": [], "safe": []})
                            path_evidence[prev_res]["leaking"].append(list(path)+[block.id])
                        del new_live[lhs]

            # 3) Release:   <handle>.close() (or .wait/.kill/.cleanup per spec)
            to_close: set[int] = set()
            for var, res_id in list(new_live.items()):
                # Find release name for this res_id
                _, acq_n, rel_name = new_res.get(res_id, ("?", "?", "close"))
                spec = next((r for r in resources if r.matches_acquire(acq_n)), None)
                alias_set = {v for v, r in new_live.items() if r == res_id}
                if _is_release(stmt, alias_set, spec, rel_name):
                    to_close.add(res_id)
            if to_close:
                for res_id in to_close:
                    # Remove all var -> res mappings for this res
                    vars_to_remove = [v for v, r in list(new_live.items()) if r == res_id]
                    for v in vars_to_remove:
                        del new_live[v]
                    # Keep new_res entry for safe-path reporting but it's now closed
                    # Remove so it won't be reported as leaked at exit, but remember it was safe on this path
                    # We need to track that this path closed it -> will be recorded in DFS safe path logic

            # 4) Ownership transfer via return: if stmt is Return(value=Name(handle))
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                transferred: set[int] = set()
                # Check if return value is a resource alias
                # Cases: return f, return (f, g), return foo(f)
                # Simplistic: if return value is Name and that name in new_live -> transfer
                if isinstance(stmt.value, ast.Name) and stmt.value.id in new_live:
                    res_id = new_live[stmt.value.id]
                    _, _, rel_name = new_res.get(res_id, ("?", "?", "close"))
                    # Find spec to know if ownership transfer allowed
                    # Look up spec by acquire name
                    orig_var, acq_name, _ = new_res[res_id]
                    spec = next((r for r in resources if r.matches_acquire(acq_name)), None)
                    if spec and spec.ownership_transferred_on_return:
                        transferred.add(res_id)
                    else:
                        # Even if not, we still consider it not leaked if returned? But we will report as leak anyway
                        # For now treat as transfer to avoid false positive for factory pattern
                        transferred.add(res_id)
                # Also: return [f], return { "f": f } — not handled; conservative leak
                # Remove transferred resources from live (they escape)
                for res_id in transferred:
                    vars_to_remove = [v for v, r in list(new_live.items()) if r == res_id]
                    for v in vars_to_remove:
                        del new_live[v]

            # Note: function calls like helper(f) where helper might close are NOT handled in MVP intraprocedural — will be reported as leak (conservative)

        return new_live, new_res, local_leaks

    # DFS over CFG with path-sensitive state
    # We enumerate all acyclic paths (loop visited once) and collect leak evidence

    # For each path, we need to know which resources were closed vs still live at exit
    # We do recursive DFS

    max_paths = 200  # guard against exponential blowup
    path_count = 0

    def dfs(block, live: dict[str, int], res_info: dict[int, tuple[str, str, str]], path: list[int], visited: set[int]):
        nonlocal path_count
        if block.id in visited:
            # Loop back edge — consider this path as one iteration then stop
            # If live resources survive loop without close, they will be caught at exit or via other path
            # For leak detection, encountering a loop without close on any iteration is not enough; we need to know if close inside loop
            # Our visited guard ensures we visit loop once — ok for hackathon
            return
        visited = visited | {block.id}
        path = path + [block.id]

        # Save state before processing block for evidence (needed for acquire in this block)
        # Actually process block's statements
        new_live, new_res, leaks_inside = _process_block(block, live, res_info, path)

        # Record leaking res found inside this block (reassign leaks)
        # They are already added to found_leaks inside _process_block; we just ensure path evidence updated for them
        # For path evidence of reassign leaks, we already pushed path

        # If this is a final/exit block, any remaining live resources are leaks
        # IMPORTANT: Scalpel marks `return` blocks as finalblocks even when they have an edge to `finally`/`close`.
        # So we must NOT treat `block in finalblocks` alone as terminal; true exits are blocks with no successors.
        # For leak detection, only blocks with no exits are genuine function exits (return/raise/fall-through).
        # However, with our patch, `try/finally` should have: try-block -> finally-block (close) -> no exit, so no false final.
        # Keep `finalblocks` check only for legacy Return phantom case, but don't trigger before processing successors.
        # Correct: is_final = (not block.exits)  OR  (block in finalblocks and not block.exits)
        # Simplistic: only consider no-exit blocks as final for live-check.
        is_final = not block.exits
        if is_final:
            path_count += 1
            if new_live:
                for var, res_id in new_live.items():
                    # Each remaining live resource is a leak on this path
                    # But we deduplicate by res_id globally
                    if res_id not in found_leaks:
                        orig_var, acq_name, rel_name = new_res.get(res_id, (var, "?", "close"))
                        # Use acquire line as res_id base
                        acq_line = res_id if res_id < 10000 else res_id // 1000
                        col = block.statements[0].col_offset if block.statements and hasattr(block.statements[0], "col_offset") else 0
                        # Find acquire stmt line for better message
                        found_leaks[res_id] = Leak(
                            file=file_path,
                            func=func_name,
                            line=acq_line,
                            col=col,
                            var=orig_var,
                            acquire=acq_name,
                            release=rel_name,
                            message=f"Resource '{orig_var}' acquired at line {acq_line} not released on all paths (leak path via blocks {path})",
                            acquire_line=acq_line,
                        )
                        path_evidence.setdefault(res_id, {"leaking": [], "safe": []})
                    path_evidence[res_id]["leaking"].append(list(path))
                # For resources that were closed or transferred along this path, they are safe on this path
                # How to know which were safe? We could track all res_ids that ever existed vs remaining
                # All res_ids that were in res_info at any point and are NOT in new_live and NOT already marked as inside-leak are safe on this path
                # For now we track safe by looking at path_evidence: those not in found_leaks in other branches?
                # Simpler: if we reached exit without live, then any resource that was created earlier and is now closed is safe on this path
                # We can compute safe by: for each res_id in new_res (which includes closed ones) that is not in new_live and not in found_leaks? But found_leaks includes inside leaks (also closed? no)
                # Instead we treat exit-with-no-leak as collecting safe evidence for all resources that existed on entry path but are closed
                # This requires tracking full history. For MVP, we just collect safe paths for resources seen as leaking via new_live check elsewhere but closed here
                # We'll enumerate safe as complement: for each res_id that appears in any leaking but is closed on this path, mark safe
                # For hackathon reporting, leaking paths are enough; safe paths are bonus
            else:
                # No live -> all resources created along path were safely closed or transferred
                # Mark safe for any res that was previously leaking? Not needed for correctness
                # We can attempt to infer: for each res_id in path_evidence that is already known to be leaking, this path being clean doesn't make it not a leak (definite leak if ANY path leaks)
                # So safe paths are just for context; we'll store them for resources that leak
                for res_id in list(path_evidence.keys()):
                    # If this res was created somewhere along this path's history, then this safe exit means safe path exists
                    # We can check if res_id's acquire line is in path's blocks' stmts
                    # For simplicity, if res_id's acquire line < block.at() and res_id not in new_live and res_id not in leaks_inside, then it's safe on this path
                    if res_id not in new_live:
                        # check if this res was live at some point on this path? We can just assume if res_id in new_res, then it was along path and now closed
                        if res_id in new_res:
                            path_evidence[res_id]["safe"].append(list(path))

        # Recurse to successors if not at max paths
        if path_count < max_paths:
            for edge in block.exits:
                dfs(edge.target, dict(new_live), dict(new_res), path, set(visited))
        else:
            # path limit hit — conservatively mark all remaining live as leaks
            pass

    dfs(entry, {}, {}, [], set())

    # Convert found_leaks dict to list, attach path evidence + human-readable
    # path summaries (statement sources along each path).
    id2b = {b.id: b for b in blocks}

    def _path_sources(path_ids: list[int]) -> list[str]:
        out: list[str] = []
        for bid in path_ids:
            blk = id2b.get(bid)
            if blk is None:
                continue
            for s in blk.statements:
                try:
                    out.append(ast.unparse(s))
                except Exception:
                    continue
        return out

    result: list[Leak] = []
    for res_id, leak in found_leaks.items():
        ev = path_evidence.get(res_id, {"leaking": [], "safe": []})
        leak.paths = ev.get("leaking", [])
        leak.safe_paths = ev.get("safe", [])
        leak.path_sources = [_path_sources(p) for p in leak.paths]
        leak.safe_path_sources = [_path_sources(p) for p in leak.safe_paths]
        result.append(leak)

    # Deduplicate leaks by acquire line (multiple aliases same resource)
    # If same acquire line leaked multiple times, keep one
    by_line: dict[int, Leak] = {}
    for lk in result:
        if lk.acquire_line not in by_line:
            by_line[lk.acquire_line] = lk
        else:
            # Merge paths
            existing = by_line[lk.acquire_line]
            existing.paths.extend(lk.paths)
            existing.safe_paths.extend(lk.safe_paths)
            existing.path_sources.extend(lk.path_sources)
            existing.safe_path_sources.extend(lk.safe_path_sources)

    return list(by_line.values())


def analyze_source_with_cfg(source: str, filename: str = "<string>", config: CodeGateConfig | None = None) -> tuple[list[Leak], any]:
    """Analyze Python source string and return (leaks, root_cfg)."""
    if config is None:
        config = CodeGateConfig.default()
    # Build the import map once (aliased/relative imports -> canonical names)
    import_map = build_import_map(ast.parse(source))
    cfg = build_cfg(source, name=filename)
    leaks: list[Leak] = []

    # Analyze each function cfg
    for (block_id, func_name), fcfg in cfg.functioncfgs.items():
        file_for_report = filename
        func_leaks = analyze_function_cfg(fcfg, func_name, file_for_report, config, import_map)
        leaks.extend(func_leaks)

    if cfg.entryblock is not None:
        has_acquire_at_top = False
        for b in get_all_blocks_filtered(cfg):
            for s in b.statements:
                if isinstance(s, ast.FunctionDef):
                    continue
                if _get_acquire_info(s, config.resources, import_map):
                    has_acquire_at_top = True
                    break
            if has_acquire_at_top:
                break
        if has_acquire_at_top:
            top_leaks = analyze_function_cfg(cfg, "<module>", filename, config, import_map)
            leaks.extend(top_leaks)

    # HARDEN-3: exception-safety pass (may-throw calls leaking live resources)
    if config.exception_safety:
        exc_leaks = analyze_exception_safety(source, leaks, config)
        leaks.extend(exc_leaks)

    return leaks, cfg


def analyze_source(source: str, filename: str = "<string>", config: CodeGateConfig | None = None) -> list[Leak]:
    """Analyze Python source string."""
    leaks, _ = analyze_source_with_cfg(source, filename, config)
    return leaks


def analyze_file_with_cfg(path: str | Path, config: CodeGateConfig | None = None) -> tuple[list[Leak], any]:
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    return analyze_source_with_cfg(src, filename=str(p), config=config)


def analyze_file(path: str | Path, config: CodeGateConfig | None = None) -> list[Leak]:
    p = Path(path)
    src = p.read_text(encoding="utf-8")
    return analyze_source(src, filename=str(p), config=config)


# ---------------------------------------------------------------------------
# Exception-path analysis (HARDEN-3)
# ---------------------------------------------------------------------------
# Rationale: the CFG above only models normal control flow. But any call can
# raise; if a resource is live when an uncaught exception propagates, it leaks.
# The classic unsound-but-common pattern:
#
#     f = open(p)
#     data = f.read()   # <- if this raises, f leaks (no finally!)
#     f.close()
#
# is reported SAFE by pure path analysis. This module catches it.
#
# Sound rules implemented:
#   A call at line L may leak live resource v iff:
#     1. acquire(v) < L  (v is live at L on the statement-order approximation)
#     2. L < first release of v (or v never released)  — after release, safe
#     3. L is NOT lexically inside a `with` body (context manager handles unwind)
#     4. L is NOT inside a try body that has at least one except handler
#        (exception is caught, control continues — no exceptional exit)
#     5. L is not the release call itself / acquire call itself
#
# Known approximation: statement-order (line) liveness, not path-sensitive.
# Nested scopes (inner defs/lambdas/classes) are excluded from the caller's
# analysis; they get analyzed as their own functions.
# ---------------------------------------------------------------------------

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _walk_own(node: ast.AST):
    """Yield descendants of node without entering nested scopes."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _SCOPE_NODES):
            continue
        yield child
        yield from _walk_own(child)


def _exception_leak_candidates(
    func_ast: ast.AST,
    acquire_line: int,
    var: str,
    release_name: str,
) -> list[tuple[int, str]]:
    """Return [(call_line, called_name)] where a raise would leak `var`.

    Per-var safe regions (exception at a line here would still release `var`):
      - try body WITH at least one except handler  (exception caught, control continues)
      - try body whose finally releases `var` via any alias
          (finally runs during unwinding -> resource released)
    NOT safe (common misconception):
      - with bodies for OUTER resources: the with's __exit__ only cleans up the
        with's own context managers; an outer `f` used inside still leaks.
      - finally bodies themselves (a call inside finally may raise).
    """
    aliases = {var}
    calls: list[ast.Call] = []
    release_lines: list[int] = []
    acquire_call: ast.Call | None = None

    # try-node records: (body_start, body_end, has_handlers, finally_closes_var)
    try_regions: list[tuple[int, int, bool, bool]] = []

    def _releases_var(stmts: list[ast.stmt]) -> bool:
        for s in stmts:
            # _walk_own(s) yields children of s, so the Expr wrapper is never
            # yielded — match the Call directly.
            for sub in _walk_own(s):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                        and sub.func.attr == release_name \
                        and isinstance(sub.func.value, ast.Name) \
                        and sub.func.value.id in aliases:
                    return True
        return False

    for n in _walk_own(func_ast):
        if isinstance(n, ast.Try):
            has_handlers = bool(n.handlers)
            fin_closes = _releases_var(n.finalbody) if n.finalbody else False
            if n.body:
                try_regions.append((n.body[0].lineno, n.body[-1].end_lineno, has_handlers, fin_closes))
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            # `with contextlib.closing(f):` DOES protect `f`: on unwinding,
            # closing.__exit__ calls f.close(). Mark (with-entry .. with-exit)
            # as a safe region for the wrapped var.
            for item in n.items:
                expr = item.context_expr
                if isinstance(expr, ast.Call):
                    fname = expr.func.attr if isinstance(expr.func, ast.Attribute) else (
                        expr.func.id if isinstance(expr.func, ast.Name) else "")
                    if fname == "closing":
                        for a in expr.args:
                            if isinstance(a, ast.Name) and (a.id == var or a.id in aliases):
                                if n.body:
                                    try_regions.append(
                                        (n.lineno, n.body[-1].end_lineno, True, False))
        elif isinstance(n, ast.Call):
            calls.append(n)
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Name):
            if n.value.id in aliases:
                aliases.add(n.targets[0].id)  # g = f  -> g is also a handle
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) \
                and isinstance(n.value.func, ast.Attribute) \
                and n.value.func.attr == release_name \
                and isinstance(n.value.func.value, ast.Name) \
                and n.value.func.value.id in aliases:
            release_lines.append(n.lineno)
        if acquire_call is None and isinstance(n, (ast.Assign, ast.AnnAssign)) \
                and getattr(n, "lineno", None) == acquire_line \
                and isinstance(n.value, ast.Call):
            acquire_call = n.value

    first_release = min(release_lines) if release_lines else None

    def is_safe(line: int) -> bool:
        for (s, e, has_handlers, fin_closes) in try_regions:
            if s <= line <= e:
                if has_handlers or fin_closes:
                    return True
        return False

    bad: list[tuple[int, str]] = []
    for c in calls:
        if c.lineno <= acquire_line:
            continue
        if acquire_call is not None and c is acquire_call:
            continue
        if first_release is not None and c.lineno >= first_release:
            continue  # resource released before this call on this order
        if is_safe(c.lineno):
            continue
        if isinstance(c.func, ast.Attribute):
            name = c.func.attr
        elif isinstance(c.func, ast.Name):
            name = c.func.id
        else:
            name = "<expr>"
        bad.append((c.lineno, name))
    return bad


def _find_enclosing_function(tree: ast.Module, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find the function whose source range contains `line` (nearest/deepest)."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= line <= (node.end_lineno or node.lineno):
                # prefer deepest (smallest range)
                if best is None or (node.end_lineno - node.lineno) < (best.end_lineno - best.lineno):
                    best = node
    return best


def _exception_leaks_for(
    tree: ast.Module,
    path_leaks: list[Leak],
    file_path: str,
) -> list[Leak]:
    """For each normal-path leak (or even safe-path acquire), check exception safety."""
    extra: list[Leak] = []
    seen_acquire: set[tuple[str, int]] = set()

    # Also check acquires that were NOT path-leaks (f=open; f.read(); f.close() is
    # path-SAFE but exception-UNSAFE). We recompute acquires per enclosing function.
    for lk in path_leaks:
        key = (lk.func, lk.acquire_line)
        if key in seen_acquire:
            continue
        seen_acquire.add(key)
        func = _find_enclosing_function(tree, lk.acquire_line)
        if func is None:
            continue
        bad_calls = _exception_leak_candidates(func, lk.acquire_line, lk.var, lk.release)
        if bad_calls:
            first_line, first_name = bad_calls[0]
            lk.exception_note = (
                f"Exception risk: if '{first_name}()' (line {first_line}) raises, "
                f"'{lk.var}' leaks too — nothing catches the error before close."
            )
            lk.kind = "path+exception"
    return extra


def analyze_exception_safety(
    source: str,
    path_leaks: list[Leak],
    config: CodeGateConfig,
) -> list[Leak]:
    """Standalone exception-safety pass.

    In addition to annotating existing path-leaks, it catches acquires that are
    path-safe but exception-unsafe (the classic no-finally pattern).
    Returns NEW exception-only leaks not already covered by a path leak.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    import_map = build_import_map(tree)

    # Collect all acquires per function from the desugared-free original AST
    new_leaks: list[Leak] = []
    annotated: set[tuple[str, int]] = set()

    # 1) Annotate existing path leaks
    _exception_leaks_for(tree, path_leaks, path_leaks[0].file if path_leaks else "<string>")
    for lk in path_leaks:
        annotated.add((lk.var, lk.acquire_line))

    # 2) Find exception-unsafe acquires that had no path leak
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for n in _walk_own(node):
            acq = _get_acquire_info(n, config.resources, import_map)
            if not acq:
                continue
            var, acq_name, rel_name = acq
            key = (var, n.lineno)
            if key in annotated:
                continue  # already reported (path leak or annotated above)
            annotated.add(key)
            bad_calls = _exception_leak_candidates(node, n.lineno, var, rel_name)
            if bad_calls:
                first_line, first_name = bad_calls[0]
                new_leaks.append(Leak(
                    file=path_leaks[0].file if path_leaks else "<string>",
                    func=node.name,
                    line=n.lineno,
                    col=getattr(n, "col_offset", 0),
                    var=var,
                    acquire=acq_name,
                    release=rel_name,
                    message=(
                        f"'{var}' = {acq_name}(...) at line {n.lineno} is not closed if an "
                        f"exception occurs: '{first_name}()' (line {first_line}) may raise "
                        f"before the close, with no try/finally or 'with' to catch it."
                    ),
                    acquire_line=n.lineno,
                    kind="exception",
                    exception_note=(
                        f"Exception risk: if '{first_name}()' (line {first_line}) raises, "
                        f"'{var}' leaks — normal paths close it, errors don't."
                    ),
                ))
    return new_leaks

