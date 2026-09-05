"""CodeGate analyzer — path-sensitive resource-leak detection on Scalpel CFG."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .api_semantics import APISemanticsResolver
from .config import CodeGateConfig, ResourceSpec
from .imports import build_import_map, resolve_call_name
from .knowledge_base import KnowledgeBase
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
    # ── Structured finding schema (CODEGATE001) ──
    rule: str = "CODEGATE001"
    # error = definite leak; warning = potential/unknown
    severity: str = "error"
    # definite = proven by CFG; potential = may escape via unknown callee
    confidence: str = "definite"
    # resource category (file/socket/db/http/process) from the matched spec
    resource_type: str = "file"
    # cleanup guarantee found by the analyzer (line of the close on safe paths)
    cleanup_line: int | None = None
    # safe | unsafe | unknown  — detection and fixability are separate
    fixability: str = "unknown"
    # labeled reasons: "early return", "exception escape", "unreleased on path", ...
    leak_reasons: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "rule": self.rule,
            "severity": self.severity,
            "confidence": self.confidence,
            "resource_type": self.resource_type,
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
            "cleanup_line": self.cleanup_line,
            "fixability": self.fixability,
            "leak_reasons": self.leak_reasons,
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
                         import_map: dict[str, str] | None = None,
                         param_effects: dict[str, dict[str, str]] | None = None,
                         lexical_flags: dict[int, dict] | None = None) -> list[Leak]:
    """Analyze a single function CFG, return leaks.

    Resource instances are tracked with unique ids (their acquisition line).
    Per-resource flags (reassigned / escaped_unknown / cleanups) accumulate
    across paths and decide confidence + fixability at leak creation:
      confidence: definite (proven) vs potential (may escape via unknown callee)
      fixability: safe | unsafe (e.g. overwrite) | unknown (loops/try/transfer)
    """
    resources = config.resources
    api_resolver = APISemanticsResolver(
        kb=KnowledgeBase(kb_path=config.kb_path),
        min_confidence=config.min_confidence,
    )
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

    # Resource-instance flags — accumulate across paths (NOT copied per path):
    #   reassigned: the handle var was overwritten while resource was live
    #   escaped_unknown: passed to an unknown external callee (may close or not)
    #   cleanups: lines of successful release calls observed on any path
    res_flags: dict[int, dict] = {}

    def _flags(res_id: int) -> dict:
        return res_flags.setdefault(res_id, {"reassigned": False, "escaped_unknown": False, "cleanups": []})

    def _finalize(leak: Leak, res_id: int, reason: str) -> Leak:
        """Resolve confidence/fixability/severity from accumulated instance flags."""
        fl = _flags(res_id)
        if reason not in leak.leak_reasons:
            leak.leak_reasons.append(reason)
        if fl.get("cleanups"):
            leak.cleanup_line = min(fl["cleanups"])
        spec = next((r for r in resources if r.matches_acquire(leak.acquire)), None)
        if spec is not None:
            leak.resource_type = _spec_type(spec)
        if fl.get("escaped_unknown"):
            leak.confidence = "potential"
            leak.severity = "warning"
            leak.fixability = "unknown"
        elif fl.get("reassigned"):
            leak.confidence = "definite"
            leak.fixability = "unsafe"
        else:
            leak.confidence = "definite"
            lf = (lexical_flags or {}).get(leak.acquire_line, {})
            if lf.get("in_loop") or lf.get("in_try"):
                leak.fixability = "unknown"
            else:
                leak.fixability = "safe"
        return leak

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
                            lk = Leak(
                                file=file_path,
                                func=func_name,
                                line=stmt.lineno,
                                col=col,
                                var=orig_var,
                                acquire=acq_n,
                                release=rel_n,
                                message=(
                                    f"Resource '{orig_var}' acquired at line {prev_res} leaked: overwritten by "
                                    f"'{var} = {acq_name}(...)' at line {stmt.lineno} before release. "
                                    f"Automatic fix not applied because removing the first acquisition "
                                    f"could change program behavior — close Resource #{prev_res} before "
                                    f"reassignment, or use separate context-managed variables."
                                ),
                                acquire_line=prev_res,
                            )
                            _flags(prev_res)["reassigned"] = True
                            found_leaks[prev_res] = _finalize(lk, prev_res, "reassignment")
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

            # 1.5) External API returning resource: var = external_library.get_file()
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and isinstance(stmt.value, ast.Call):
                target_var = None
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    target_var = stmt.targets[0].id
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    target_var = stmt.target.id

                if target_var:
                    cname = _call_name(stmt.value)
                    if cname:
                        resolved_cname = resolve_call_name(cname, import_map)
                        if not any(r.matches_acquire(resolved_cname) for r in resources):
                            is_local_func = (
                                param_effects is not None
                                and (resolved_cname in param_effects or cname in param_effects)
                            )
                            if not is_local_func:
                                contract = api_resolver.resolve_call(resolved_cname, resource_type="FILE")
                                if contract.behavior in ("RETURNS_RESOURCE", "CREATES_RESOURCE") or contract.ownership == "RETURN":
                                    res_id = stmt.lineno
                                    orig_res_id = res_id
                                    counter = 0
                                    while res_id in new_res:
                                        counter += 1
                                        res_id = orig_res_id * 1000 + counter
                                    new_live[target_var] = res_id
                                    new_res[res_id] = (target_var, resolved_cname, "close")
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
                                    lk = Leak(
                                        file=file_path, func=func_name, line=stmt.lineno, col=col,
                                        var=orig_var, acquire=acq_n, release=rel_n,
                                        message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: alias '{lhs}' overwritten",
                                        acquire_line=prev_res,
                                    )
                                    _flags(prev_res)["reassigned"] = True
                                    found_leaks[prev_res] = _finalize(lk, prev_res, "reassignment")
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
                                    lk = Leak(
                                        file=file_path, func=func_name, line=stmt.lineno, col=col,
                                        var=orig_var, acquire=acq_n, release=rel_n,
                                        message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: handle '{lhs}' overwritten by non-resource at line {stmt.lineno}",
                                        acquire_line=prev_res,
                                    )
                                    _flags(prev_res)["reassigned"] = True
                                    found_leaks[prev_res] = _finalize(lk, prev_res, "reassignment")
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
                                lk = Leak(
                                    file=file_path, func=func_name, line=stmt.lineno, col=col,
                                    var=orig_var, acquire=acq_n, release=rel_n,
                                    message=f"Resource '{orig_var}' acquired at line {prev_res} leaked: overwritten at line {stmt.lineno}",
                                    acquire_line=prev_res,
                                )
                                _flags(prev_res)["reassigned"] = True
                                found_leaks[prev_res] = _finalize(lk, prev_res, "reassignment")
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
                    # record cleanup guarantee for diagnostics/fixability
                    if hasattr(stmt, "lineno"):
                        _flags(res_id)["cleanups"].append(stmt.lineno)
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

            # 3.5) Interprocedural and External API call sites: helper(f) or ext_lib.process(f)
            call_node = None
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call_node = stmt.value
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)) and isinstance(stmt.value, ast.Call):
                call_node = stmt.value

            if call_node is not None:
                cname = _call_name(call_node)
                if cname:
                    resolved_cname = resolve_call_name(cname, import_map)
                    is_local_func = (
                        param_effects is not None
                        and (resolved_cname in param_effects or cname in param_effects)
                    )

                    if is_local_func and param_effects is not None:
                        callee_info = param_effects.get(resolved_cname) or param_effects.get(cname)
                        if callee_info:
                            callee_params = callee_info.get("params", [])
                            effects_map = callee_info.get("effects", {})
                            for pos, argnode in enumerate(call_node.args):
                                if not (isinstance(argnode, ast.Name) and argnode.id in new_live):
                                    continue
                                param = callee_params[pos] if pos < len(callee_params) else None
                                effect = effects_map.get(param, "unknown") if param else "unknown"
                                res_id = new_live[argnode.id]
                                if effect in ("releases", "escapes"):
                                    for v in [v for v, r in list(new_live.items()) if r == res_id]:
                                        del new_live[v]
                                elif effect == "leaks":
                                    other_holders = [v for v, r in new_live.items() if r == res_id and v != argnode.id]
                                    if not other_holders:
                                        orig_var, acq_n, rel_n = new_res.get(res_id, (argnode.id, "?", "close"))
                                        if res_id not in found_leaks:
                                            col = stmt.col_offset if hasattr(stmt, "col_offset") else 0
                                            lk = Leak(
                                                file=file_path, func=func_name, line=stmt.lineno, col=col,
                                                var=orig_var, acquire=acq_n, release=rel_n,
                                                message=(
                                                    f"Resource '{orig_var}' acquired at line {res_id} leaked: "
                                                    f"passed to '{cname}()' at line {stmt.lineno}, which never "
                                                    f"closes its parameter on some path inside it"
                                                ),
                                                acquire_line=res_id,
                                            )
                                            found_leaks[res_id] = _finalize(lk, res_id, f"leaked inside callee '{cname}()'")
                                            path_evidence.setdefault(res_id, {"leaking": [], "safe": []})
                                        path_evidence[res_id]["leaking"].append(list(path) + [block.id])
                                        local_leaks.append(res_id)
                                        for v in [v for v, r in list(new_live.items()) if r == res_id]:
                                            del new_live[v]
                                else:
                                    _flags(res_id)["escaped_unknown"] = True
                                    _flags(res_id).setdefault("unknown_callees", set()).add(cname)
                    else:
                        # External library API call site
                        has_live_arg = any(isinstance(a, ast.Name) and a.id in new_live for a in call_node.args)
                        if has_live_arg:
                            for argnode in call_node.args:
                                if isinstance(argnode, ast.Name) and argnode.id in new_live:
                                    res_id = new_live[argnode.id]
                                    orig_v, acq_n, _ = new_res.get(res_id, (argnode.id, "FILE", "close"))
                                    spec = next((r for r in resources if r.matches_acquire(acq_n)), None)
                                    res_type = _spec_type(spec).upper() if spec else "FILE"

                                    contract = api_resolver.resolve_call(resolved_cname, resource_type=res_type)

                                    if contract.behavior in ("CLOSES_INPUT", "TRANSFERS_OWNERSHIP") or contract.ownership in ("CONSUME", "TRANSFER"):
                                        if hasattr(stmt, "lineno"):
                                            _flags(res_id)["cleanups"].append(stmt.lineno)
                                        for v in [v for v, r in list(new_live.items()) if r == res_id]:
                                            del new_live[v]
                                    elif contract.behavior == "PRESERVES_INPUT" or contract.ownership == "BORROW":
                                        pass
                                    else:
                                        _flags(res_id)["escaped_unknown"] = True
                                        _flags(res_id).setdefault("unknown_callees", set()).add(resolved_cname)

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
            # Loop back edge (continue / end-of-body loop-back / break).
            # Resources acquired INSIDE the loop body that are still live on
            # this back-edge are orphaned for this iteration: the next
            # iteration acquires a new instance while the old one is never
            # released (e.g. `continue` bypassing the close). Resources
            # acquired OUTSIDE the loop legitimately stay live across
            # iterations, so they are exempt (lexical check).
            for var, res_id in list(live.items()):
                if res_id in found_leaks:
                    continue
                acq_line = res_id if res_id < 10000 else res_id // 1000
                lf = (lexical_flags or {}).get(acq_line, {})
                if not lf.get("in_loop"):
                    continue
                orig_var, acq_name, rel_name = res_info.get(res_id, (var, "?", "close"))
                col = 0
                lk = Leak(
                    file=file_path, func=func_name, line=acq_line, col=col,
                    var=orig_var, acquire=acq_name, release=rel_name,
                    message=(
                        f"Resource '{orig_var}' acquired at line {acq_line} inside a loop is not "
                        f"released before the loop back-edge (continue/break path) — each such "
                        f"iteration orphans the previous instance (leak path via blocks {path})"
                    ),
                    acquire_line=acq_line,
                )
                found_leaks[res_id] = _finalize(lk, res_id, "loop bypass (continue/break)")
                path_evidence.setdefault(res_id, {"leaking": [], "safe": []})
                path_evidence[res_id]["leaking"].append(list(path))
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
            # reason label from the terminal block's shape (§22)
            has_return = any(isinstance(s, ast.Return) for s in block.statements)
            has_raise = any(isinstance(s, ast.Raise) for s in block.statements)
            reason = ("exception escape" if has_raise
                      else "early return" if has_return else "fall-through exit")
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
                        fl = _flags(res_id)
                        if fl.get("escaped_unknown"):
                            callees = ", ".join(sorted(fl.get("unknown_callees", {"unknown"})))
                            msg = (
                                f"Resource '{orig_var}' acquired at line {acq_line} may not be released: "
                                f"it may escape via unknown external call(s) '{callees}', whose cleanup "
                                f"behavior cannot be proven (potential leak, paths {path})"
                            )
                        else:
                            msg = f"Resource '{orig_var}' acquired at line {acq_line} not released on all paths (leak path via blocks {path})"
                        lk = Leak(
                            file=file_path,
                            func=func_name,
                            line=acq_line,
                            col=col,
                            var=orig_var,
                            acquire=acq_name,
                            release=rel_name,
                            message=msg,
                            acquire_line=acq_line,
                        )
                        found_leaks[res_id] = _finalize(lk, res_id, reason)
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


def sync_kb_and_resolve_unknowns(tree: ast.AST, config: CodeGateConfig, import_map: dict[str, str]) -> KnowledgeBase:
    """Sync KnowledgeBase resources and api_contracts into config.resources.
    Also scan AST for unknown external function calls (e.g. pymongo.MongoClient, h5py.File)
    and query APISemanticsResolver (KB -> LLM fallback -> write to resources.yaml).
    """
    kb = KnowledgeBase(kb_path=config.kb_path)

    # 1. Load resources from kb.resources
    for r_dict in kb.resources:
        call = r_dict.get("call")
        if not call:
            continue
        rel = r_dict.get("close", ["close"])
        primary_rel = rel[0] if rel else "close"
        alt_rel = rel[1:] if len(rel) > 1 else r_dict.get("alt_releases", [])
        if not any(spec.matches_acquire(call) for spec in config.resources):
            config.resources.append(ResourceSpec(acquire=call, release=primary_rel, alt_releases=alt_rel))

    # 2. Load API contracts from kb.contracts
    for contract in kb.contracts:
        if contract.behavior in ("RETURNS_RESOURCE", "CREATES_RESOURCE") or contract.ownership == "RETURN":
            call_name = f"{contract.library}.{contract.function}" if contract.library and contract.library != "builtins" else contract.function
            if not any(spec.matches_acquire(call_name) for spec in config.resources):
                rel = "aclose" if "async" in call_name.lower() else "close"
                config.resources.append(ResourceSpec(acquire=call_name, release=rel))

    # 3. Scan AST for unknown external library function calls
    api_resolver = APISemanticsResolver(kb=kb, min_confidence=config.min_confidence)
    for node in ast.walk(tree):
        call_node = None
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Call):
            call_node = node.value
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call_node = node.value

        if call_node is not None:
            cname = _call_name(call_node)
            if cname:
                resolved_cname = resolve_call_name(cname, import_map)
                # Only check external dotted library calls not already in config.resources
                if ("." in resolved_cname or "." in cname) and not any(r.matches_acquire(resolved_cname) or r.matches_acquire(cname) for r in config.resources):
                    contract = api_resolver.resolve_call(resolved_cname, resource_type="FILE")
                    if contract and (contract.behavior in ("RETURNS_RESOURCE", "CREATES_RESOURCE") or contract.ownership == "RETURN"):
                        rel = "aclose" if "async" in resolved_cname.lower() else "close"
                        if not any(r.matches_acquire(resolved_cname) for r in config.resources):
                            config.resources.append(ResourceSpec(acquire=resolved_cname, release=rel))

    return kb


def analyze_source_with_cfg(source: str, filename: str = "<string>", config: CodeGateConfig | None = None) -> tuple[list[Leak], any]:
    """Analyze Python source string and return (leaks, root_cfg)."""
    if config is None:
        config = CodeGateConfig.default()
    parsed_ast = ast.parse(source)
    # Build the import map once (aliased/relative imports -> canonical names)
    import_map = build_import_map(parsed_ast)
    
    # Resolve unknown external library APIs via KB / LLM fallback and update resources.yaml
    sync_kb_and_resolve_unknowns(parsed_ast, config, import_map)

    cfg = build_cfg(source, name=filename)
    leaks: list[Leak] = []

    # Interprocedural pass: per-function parameter effects, computed once.
    # Consulted at call sites (helper(f) etc.) during the path DFS.
    from .interproc import compute_param_effects
    param_effects = compute_param_effects(cfg)

    # Lexical context per acquire line (loop/try body) — fixes fixability.
    lexical_flags = _lexical_resource_flags(parsed_ast)

    # Analyze each function cfg
    for (block_id, func_name), fcfg in cfg.functioncfgs.items():
        file_for_report = filename
        func_leaks = analyze_function_cfg(fcfg, func_name, file_for_report, config,
                                          import_map, param_effects, lexical_flags)
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
            top_leaks = analyze_function_cfg(cfg, "<module>", filename, config,
                                             import_map, param_effects, lexical_flags)
            leaks.extend(top_leaks)

    # HARDEN-3: exception-safety pass (may-throw calls leaking live resources)
    if config.exception_safety:
        exc_leaks = analyze_exception_safety(source, leaks, config)
        leaks.extend(exc_leaks)

    # Merge overlapping findings on the same variable (§7/§19): when a variable
    # has BOTH a definite path leak (e.g. reassignment) AND an exception finding,
    # fold the exception reason into the path finding instead of reporting two
    # separate records (reduces noise; the second finding is a secondary aspect
    # of the same resource lifetime).
    leaks = _merge_duplicate_findings(leaks)

    return leaks, cfg


def _merge_duplicate_findings(leaks: list[Leak]) -> list[Leak]:
    """Merge exception findings into same-(func,var) path findings.

    Rule: if a function has a path-leak for variable V (kind path/path+exception)
    AND a separate exception-only finding for the same V, the exception finding
    is folded into the path finding's reasons and dropped. This prevents
    double-reporting overwrite+exception on the same resource variable.
    """
    path_by_key: dict[tuple[str, str], Leak] = {}
    for lk in leaks:
        if lk.kind in ("path", "path+exception"):
            key = (lk.func, lk.var)
            # prefer the primary (lower acquire_line / earlier) instance
            if key not in path_by_key or lk.acquire_line < path_by_key[key].acquire_line:
                path_by_key[key] = lk

    merged: list[Leak] = []
    for lk in leaks:
        if lk.kind == "exception":
            key = (lk.func, lk.var)
            primary = path_by_key.get(key)
            if primary is not None:
                # fold: append the exception reason to the primary finding
                if "exception escape" not in primary.leak_reasons:
                    primary.leak_reasons.append("exception escape")
                if not primary.exception_note and lk.exception_note:
                    primary.exception_note = lk.exception_note
                continue  # drop the standalone exception finding
        merged.append(lk)
    return merged


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


def _spec_type(spec: ResourceSpec) -> str:
    """Categorize a resource spec for structured diagnostics."""
    a = spec.acquire
    if "socket" in a:
        return "socket"
    if any(k in a for k in ("sqlite", "psycopg", "mysql", "pymongo", "mongo")):
        return "database"
    if any(k in a for k in ("requests", "httpx")):
        return "http"
    if any(k in a for k in ("Popen", "Process", "subprocess", "multiprocessing")):
        return "process"
    if "tempfile" in a:
        return "tempfile"
    return "file"


def _lexical_resource_flags(tree: ast.AST) -> dict[int, dict]:
    """Per acquire-line lexical context: inside a loop body or try body?
    Used for fixability: wrapping loop/try code in `with` is not proven safe.
    """
    flags: dict[int, dict] = {}

    def visit(node: ast.AST, in_loop: bool, in_try: bool) -> None:
        for child in ast.iter_child_nodes(node):
            c_loop = in_loop or isinstance(child, (ast.For, ast.While, ast.AsyncFor))
            c_try = in_try or isinstance(child, ast.Try)
            if isinstance(child, (ast.Assign, ast.AnnAssign)) and isinstance(child.value, ast.Call):
                flags.setdefault(child.lineno, {})["in_loop"] = c_loop
                flags.setdefault(child.lineno, {})["in_try"] = c_try
            visit(child, c_loop, c_try)

    visit(tree, False, False)
    return flags


# Calls that are effectively pure / cannot realistically raise (§15: consistent
# unknown-call policy — do not assume every call definitely throws).
_PURE_BUILTINS = {
    "print", "range", "len", "int", "str", "float", "bool", "bytes", "list",
    "dict", "set", "tuple", "frozenset", "isinstance", "issubclass", "sorted",
    "reversed", "enumerate", "zip", "map", "filter", "min", "max", "sum",
    "abs", "round", "repr", "hash", "id", "type", "super", "ord", "chr",
    "divmod", "pow", "slice", "staticmethod", "classmethod",
}


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
    config: CodeGateConfig | None = None,
    import_map: dict[str, str] | None = None,
    api_resolver: APISemanticsResolver | None = None,
) -> list[tuple[int, str, str]]:
    """Return [(call_line, called_name, exc_safety)] where a raise would leak `var`.

    Per-var safe regions (exception at a line here would still release `var`):
      - try body WITH at least one except handler  (exception caught, control continues)
      - try body whose finally releases `var` via any alias
          (finally runs during unwinding -> resource released)
    """
    if config is None:
        config = CodeGateConfig.default()
    if import_map is None:
        import_map = {}
    if api_resolver is None:
        api_resolver = APISemanticsResolver(kb=KnowledgeBase(kb_path=config.kb_path), min_confidence=config.min_confidence)

    aliases = {var}
    calls: list[ast.Call] = []
    release_lines: list[int] = []
    acquire_call: ast.Call | None = None

    # try-node records: (body_start, body_end, has_handlers, finally_closes_var)
    try_regions: list[tuple[int, int, bool, bool]] = []

    def _releases_var(stmts: list[ast.stmt]) -> bool:
        for s in stmts:
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
            if isinstance(n.func, ast.Name) and n.func.id in _PURE_BUILTINS:
                continue
            calls.append(n)
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Name):
            if n.value.id in aliases:
                aliases.add(n.targets[0].id)
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

    # Check for guaranteed releases/transfers via external API calls
    guaranteed_release_lines: list[int] = list(release_lines)
    for c in calls:
        if c.lineno <= acquire_line:
            continue
        cname = _call_name(c)
        if cname:
            resolved_cname = resolve_call_name(cname, import_map)
            spec = next((r for r in config.resources if r.matches_acquire(resolved_cname)), None)
            if spec and _is_release(ast.Expr(value=c), aliases, spec, release_name):
                guaranteed_release_lines.append(c.lineno)
            else:
                has_var_arg = any(isinstance(a, ast.Name) and a.id in aliases for a in c.args)
                is_obj_method = isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) and c.func.value.id in aliases
                if has_var_arg or is_obj_method:
                    contract = api_resolver.resolve_call(resolved_cname, resource_type="FILE")
                    if contract and (contract.behavior in ("CLOSES_INPUT", "TRANSFERS_OWNERSHIP") or contract.ownership in ("CONSUME", "TRANSFER")):
                        if contract.exception_safety == "GUARANTEED":
                            guaranteed_release_lines.append(c.lineno)

    first_release = min(guaranteed_release_lines) if guaranteed_release_lines else None

    def is_safe(line: int) -> bool:
        for (s, e, has_handlers, fin_closes) in try_regions:
            if s <= line <= e:
                if has_handlers or fin_closes:
                    return True
        return False

    bad: list[tuple[int, str, str]] = []
    # Find the resource spec for this acquire so we know alt_releases (used for _is_release checks)
    _release_spec = next(
        (r for r in config.resources if r.release == release_name or release_name in r.alt_releases),
        None,
    )

    for c in calls:
        if c.lineno <= acquire_line:
            continue
        if acquire_call is not None and c is acquire_call:
            continue

        # Skip direct release calls on the tracked variable (e.g. f.close() in finally:)
        if _is_release(ast.Expr(value=c), aliases, _release_spec, release_name):
            continue

        if is_safe(c.lineno):
            continue
        if first_release is not None and c.lineno > first_release:
            continue

        cname = _call_name(c) or (c.func.attr if isinstance(c.func, ast.Attribute) else (c.func.id if isinstance(c.func, ast.Name) else "<expr>"))
        resolved_cname = resolve_call_name(cname, import_map) if cname else ""

        # Check if c IS a release or transfer call at first_release
        if first_release is not None and c.lineno == first_release:
            has_var_arg = any(isinstance(a, ast.Name) and a.id in aliases for a in c.args)
            is_obj_method = isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) and c.func.value.id in aliases
            if has_var_arg or is_obj_method:
                contract = api_resolver.resolve_call(resolved_cname, resource_type="FILE") if resolved_cname else None
                if contract and (contract.behavior in ("CLOSES_INPUT", "TRANSFERS_OWNERSHIP") or contract.ownership in ("CONSUME", "TRANSFER")):
                    if contract.exception_safety == "GUARANTEED":
                        continue  # GUARANTEED cleanup/transfer call is NOT a bad call
                    else:
                        bad.append((c.lineno, cname, contract.exception_safety))
                        continue

        contract_safety = "UNKNOWN"
        if resolved_cname:
            contract = api_resolver.resolve_call(resolved_cname, resource_type="FILE")
            if contract:
                contract_safety = contract.exception_safety

        bad.append((c.lineno, cname, contract_safety))

    return bad


def _find_enclosing_function(tree: ast.Module, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find the function whose source range contains `line` (nearest/deepest)."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= line <= (node.end_lineno or node.lineno):
                if best is None or (node.end_lineno - node.lineno) < (best.end_lineno - best.lineno):
                    best = node
    return best


def _exception_leaks_for(
    tree: ast.Module,
    path_leaks: list[Leak],
    file_path: str,
    config: CodeGateConfig | None = None,
    import_map: dict[str, str] | None = None,
    api_resolver: APISemanticsResolver | None = None,
) -> list[Leak]:
    """For each normal-path leak (or even safe-path acquire), check exception safety."""
    extra: list[Leak] = []
    seen_acquire: set[tuple[str, int]] = set()

    for lk in path_leaks:
        key = (lk.func, lk.acquire_line)
        if key in seen_acquire:
            continue
        seen_acquire.add(key)
        func = _find_enclosing_function(tree, lk.acquire_line)
        if func is None:
            continue
        bad_calls = _exception_leak_candidates(func, lk.acquire_line, lk.var, lk.release, config, import_map, api_resolver)
        if bad_calls:
            first_line, first_name, exc_safety = bad_calls[0]
            if exc_safety == "NOT_GUARANTEED":
                lk.exception_note = (
                    f"Exception risk: '{first_name}()' (line {first_line}) closes/transfers ownership on normal path, "
                    f"but its exception-safety contract is NOT_GUARANTEED. If the call raises, '{lk.var}' may leak."
                )
            else:
                lk.exception_note = (
                    f"Exception risk: if '{first_name}()' (line {first_line}) raises, "
                    f"'{lk.var}' leaks — normal paths close it, errors don't."
                )
            lk.kind = "path+exception"
    return extra


def _non_raising_functions(tree: ast.AST) -> set[str]:
    """Local functions whose bodies provably cannot raise."""
    has_call: set[str] = set()
    bodies: dict[str, list[ast.stmt]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bodies[node.name] = node.body
            for n in _walk_own(node):
                if isinstance(n, ast.Call):
                    has_call.add(node.name)
                    break
    changed = True
    while changed:
        changed = False
        for name, body in bodies.items():
            if name in has_call:
                continue
            for n in _walk_own(ast.Module(body=body, type_ignores=[])):  # type: ignore[arg-type]
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in has_call:
                    has_call.add(name)
                    changed = True
                    break
    return set(bodies) - has_call


def analyze_exception_safety(
    source: str,
    path_leaks: list[Leak],
    config: CodeGateConfig,
) -> list[Leak]:
    """Standalone exception-safety pass."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    import_map = build_import_map(tree)
    api_resolver = APISemanticsResolver(
        kb=KnowledgeBase(kb_path=config.kb_path),
        min_confidence=config.min_confidence,
    )

    new_leaks: list[Leak] = []
    annotated: set[tuple[str, int]] = set()

    # 1) Annotate existing path leaks
    _exception_leaks_for(tree, path_leaks, path_leaks[0].file if path_leaks else "<string>", config, import_map, api_resolver)
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
                continue
            annotated.add(key)
            bad_calls = _exception_leak_candidates(node, n.lineno, var, rel_name, config, import_map, api_resolver)
            if bad_calls:
                first_line, first_name, exc_safety = bad_calls[0]
                spec = next((r for r in config.resources if r.matches_acquire(acq_name)), None)
                if exc_safety == "NOT_GUARANTEED":
                    note = (
                        f"Exception risk: '{first_name}()' (line {first_line}) closes/transfers ownership on normal path, "
                        f"but its exception-safety contract is NOT_GUARANTEED. If the call raises, '{var}' may leak."
                    )
                else:
                    note = (
                        f"Exception risk: if '{first_name}()' (line {first_line}) raises, "
                        f"'{var}' leaks — normal paths close it, errors don't."
                    )
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
                    severity="error",
                    confidence="definite",
                    resource_type=_spec_type(spec) if spec else "file",
                    fixability="unknown",
                    leak_reasons=["exception escape"],
                    exception_note=note,
                ))
    return new_leaks

