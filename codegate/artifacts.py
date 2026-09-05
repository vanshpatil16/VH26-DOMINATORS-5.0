"""JSON serializers for CodeGate artifacts (AST tree, CFG graph, leaks).

These feed the GUI: the Trajectory tab renders raw payloads, the AST tab
renders the tree, the CFG tab renders blocks/edges as a node graph.
"""

from __future__ import annotations

import ast
from typing import Any

from .analyzer import Leak
from .report import _branch_labels, _stmt_src

_AST_NODE_BUDGET = 600
_AST_MAX_DEPTH = 10


def _ast_label(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        v = node.value
        s = repr(v)
        return _short(s, 24)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f"def {node.name}()"
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    if isinstance(node, ast.Attribute):
        return f".{node.attr}"
    if isinstance(node, ast.arg):
        return node.arg
    if isinstance(node, ast.Call):
        try:
            return f"{_short(ast.unparse(node.func), 24)}(...)"
        except Exception:
            return "(...)"
    if isinstance(node, ast.Assign):
        return "="
    if isinstance(node, ast.If):
        return "if"
    if isinstance(node, ast.For):
        return "for"
    if isinstance(node, ast.While):
        return "while"
    if isinstance(node, ast.With):
        return "with"
    if isinstance(node, ast.Try):
        return "try"
    if isinstance(node, ast.Match):
        return "match"
    if isinstance(node, ast.Return):
        return "return"
    if isinstance(node, ast.Expr):
        return "expr"
    return type(node).__name__


def _short(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def ast_to_json(tree: ast.AST, *, max_depth: int = _AST_MAX_DEPTH,
                node_budget: int = _AST_NODE_BUDGET) -> dict[str, Any]:
    """AST → {id,type,label,line,children[]} tree (budget-capped)."""
    counter = {"n": 0}

    def conv(node: ast.AST, depth: int) -> dict[str, Any]:
        counter["n"] += 1
        j: dict[str, Any] = {
            "id": f"n{counter['n']}",
            "type": type(node).__name__,
            "label": _ast_label(node),
            "line": getattr(node, "lineno", None),
            "children": [],
        }
        if depth >= max_depth or counter["n"] >= node_budget:
            if depth >= max_depth and ast.iter_child_nodes(node).__next__ is not None:
                j["truncated"] = True
            return j
        for child in ast.iter_child_nodes(node):
            j["children"].append(conv(child, depth + 1))
        return j

    return conv(tree, 0)


def _safe_json(obj):
    """Convert non-JSON-serializable types to strings."""
    if isinstance(obj, bytes):
        return repr(obj)
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_json(v) for v in obj]
    return obj


def _block_json(block) -> dict[str, Any]:
    stmts = [_short(_stmt_src(s).splitlines()[0], 80) for s in block.statements]
    linenos = [s.lineno for s in block.statements if hasattr(s, "lineno")]
    return {
        "id": block.id,
        "statements": stmts,
        "lineStart": min(linenos) if linenos else None,
        "lineEnd": max(linenos) if linenos else None,
        "isEntry": False,  # set by caller
        "isExit": len(block.exits) == 0,
        "funcCalls": [_safe_json(fc) for fc in (getattr(block, "func_calls", []) or [])],
    }


def cfg_to_json(cfg, leaks: list[Leak] | None = None) -> list[dict[str, Any]]:
    """Root CFG → per-function graph JSON for the GUI node renderer."""
    from .scalpel_patch import get_all_blocks_filtered

    leaks = leaks or []
    funcs: list[dict[str, Any]] = []

    def render_one(fcfg, name: str, owning_leaks: list[Leak]):
        blocks = get_all_blocks_filtered(fcfg)
        if not blocks:
            return
        entry = fcfg.entryblock if fcfg.entryblock in blocks else blocks[0]
        leak_ids: set[int] = set()
        safe_ids: set[int] = set()
        for lk in owning_leaks:
            for p in lk.paths:
                leak_ids.update(p)
            for p in lk.safe_paths:
                safe_ids.update(p)

        block_list = []
        for b in blocks:
            bj = _block_json(b)
            bj["isEntry"] = b is entry
            bj["tag"] = "leak" if b.id in leak_ids else ("safe" if b.id in safe_ids else None)
            block_list.append(bj)

        edges = []
        for b in blocks:
            labels = _branch_labels(b.exits)
            for i, e in enumerate(b.exits):
                edges.append({
                    "from": b.id,
                    "to": e.target.id,
                    "label": labels[i],
                })

        funcs.append({
            "name": name,
            "blocks": block_list,
            "edges": edges,
            "leakBlocks": sorted(leak_ids),
            "safeBlocks": sorted(safe_ids),
            "hasLeak": bool(leak_ids & {b.id for b in blocks}),
        })

    for (_, fname), fcfg in cfg.functioncfgs.items():
        owning = [lk for lk in leaks if lk.func == fname]
        render_one(fcfg, fname, owning)
    if cfg.entryblock is not None:
        render_one(cfg, "<module>", [lk for lk in leaks if lk.func == "<module>"])
    return funcs


def leaks_to_json(leaks: list[Leak]) -> list[dict[str, Any]]:
    return [lk.to_dict() for lk in leaks]
