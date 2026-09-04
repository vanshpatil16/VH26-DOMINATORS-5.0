"""Interprocedural pass — parameter-effects analysis.

Question answered per helper: "When a live resource handle is passed to this
function, what happens to it?"

    def helper(f):
        f.close()          # effect: RELEASES  (caller's resource is safe)

    def bad(g):
        if x: g.close()    # effect: LEAKS     (some path never closes)
        return 1

    def factory(h):
        return h           # effect: ESCAPES   (ownership transferred out)

Effects computed with the same DFS/state machine as the intraprocedural
engine, but seeded with `live = {param}` and using a generic release
method (param types are unknown, "close" covers the tracked resources).
"""

from __future__ import annotations

import ast
from typing import Optional

from .scalpel_patch import get_all_blocks_filtered

RELEASE_METHOD = "close"

# effect ∈ {"releases", "escapes", "leaks", "unknown"}
ParamEffects = dict[str, dict[str, str]]


def _call_base_name(call: ast.Call) -> Optional[str]:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _walk_own(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        yield child
        yield from _walk_own(child)


def _path_outcome(fcfg, param: str) -> str:
    """DFS every path from entry, tracking only `param`. Returns aggregate effect."""
    blocks = get_all_blocks_filtered(fcfg)
    if not blocks:
        return "unknown"
    entry = fcfg.entryblock if fcfg.entryblock in blocks else blocks[0]
    res_id = 0

    outcomes: set[str] = set()

    def is_release(stmt: ast.AST, aliases: set[str]) -> bool:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == RELEASE_METHOD:
                return isinstance(call.func.value, ast.Name) and call.func.value.id in aliases
        return False

    def process(block: ast.AST, live_aliases: set[str]) -> tuple[bool, Optional[str], set[str]]:
        """Returns (terminated, outcome_for_this_path, new_aliases).
        terminated=True means the resource's fate on this path is decided
        (released / escaped / leaked) — don't walk successors.
        outcome None means continue walking."""
        aliases = set(live_aliases)
        for stmt in block.statements:
            # release: x.close() where x aliases param
            if is_release(stmt, aliases):
                outcomes.add("releases")
                return True, "releases", aliases
            # escape: return x / return x.attr
            if isinstance(stmt, ast.Return) and stmt.value is not None:
                escaped = isinstance(stmt.value, ast.Name) and stmt.value.id in aliases
                if not escaped:
                    for n in _walk_own(stmt.value):
                        if isinstance(n, ast.Name) and n.id in aliases:
                            escaped = True
                            break
                if escaped:
                    outcomes.add("escapes")
                    return True, "escapes", aliases
            # overwrite of the param (or last alias holder) with a new acquire
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                lhs = stmt.targets[0].id
                if lhs in aliases and isinstance(stmt.value, ast.Call):
                    outcomes.add("leaks")
                    return True, "leaks", aliases
                # alias chain: y = x
                if isinstance(stmt.value, ast.Name):
                    rhs = stmt.value.id
                    if rhs in aliases and lhs not in aliases:
                        aliases.add(lhs)
                # kill: param reassigned to non-acquire non-alias
                elif lhs in aliases:
                    # careful: plain reassignment without acquire — resource
                    # handle lost without release on this path
                    outcomes.add("leaks")
                    return True, "leaks", aliases
        return False, None, aliases

    def dfs(block, aliases: set[str], visited: set[int]):
        if block.id in visited:
            return  # loop — one visit is enough for existence questions
        visited = visited | {block.id}
        terminated, outcome, new_aliases = process(block, aliases)
        if terminated or not block.exits:
            if not terminated and new_aliases:
                outcomes.add("leaks")  # exit with handle still live
            return
        for edge in block.exits:
            dfs(edge.target, set(new_aliases), visited)

    dfs(entry, {param}, set())

    if outcomes == {"releases"}:
        return "releases"
    if "escapes" in outcomes:
        return "escapes"
    if "leaks" in outcomes:
        return "leaks"
    return "unknown"


def compute_param_effects(cfg_root) -> ParamEffects:
    """For every local function in the module, compute per-parameter effect.

    Returns: {fname: {"params": [param names in order], "effects": {param: effect}}}
    Call-site lookup is POSITIONAL: call arg i ↔ params[i].
    """
    effects: ParamEffects = {}
    for (_, fname), fcfg in cfg_root.functioncfgs.items():
        args = cfg_root.function_args.get((_, fname), [])
        per_param = {arg: _path_outcome(fcfg, arg) for arg in args}
        if args:
            effects[fname] = {"params": args, "effects": per_param}
    return effects
