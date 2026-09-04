"""CodeGate Web API — full analysis as one JSON document (with trajectory).

Contract (used by the GUI bridge):
    python -m codegate.webapi file.py [--fix] [--filename name.py]
    echo "$SRC" | python -m codegate.webapi - [--fix]

stdout: single JSON object:
    { ok, filename, summary, leaks, trajectory, ast, cfg, fix }
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import time
from typing import Any

from .analyzer import (
    Leak,
    _get_acquire_info,
    analyze_exception_safety,
    analyze_source_with_cfg,
)
from .artifacts import ast_to_json, cfg_to_json, leaks_to_json
from .config import CodeGateConfig
from .desugar import MatchDesugarer
from .trajectory import Trajectory


def analyze_full(
    source: str,
    filename: str = "input.py",
    fix: bool = False,
    config: CodeGateConfig | None = None,
    ensemble: bool = False,
) -> dict[str, Any]:
    if config is None:
        config = CodeGateConfig.default()
    t = Trajectory()
    t0 = time.perf_counter()

    # ------------------------------------------------------------------ 1 parse
    tree: ast.Module | None = None
    with t.step("parse", "Parse source with Python ast") as s:
        tree = ast.parse(source)
        nstmt = len(tree.body)
        nfuncs = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
        nclasses = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        s.detail = f"{nstmt} top-level statements · {nfuncs} functions · {nclasses} classes"
        s.data = {
            "topLevelStatements": nstmt,
            "functions": nfuncs,
            "classes": nclasses,
            "totalLines": source.count("\n") + 1,
        }

    # --------------------------------------------------------------- 2 desugar
    with t.step("desugar", "Desugar match statements → if/elif") as s:
        matches = sum(isinstance(n, ast.Match) for n in ast.walk(tree))
        tree = MatchDesugarer().visit(tree)
        ast.fix_missing_locations(tree)
        s.detail = f"{matches} match statement(s) transformed" if matches else "no match statements found"
        s.data = {"matchStatements": matches}

    # ------------------------------------------------------------- 3 CFG build
    cfg_root = None
    with t.step("cfg", "Build control-flow graph (Scalpel CFG + CodeGate patches)") as s:
        from .scalpel_patch import build_cfg, get_all_blocks_filtered
        cfg_root = build_cfg(source, name=filename)
        fn_stats = []
        for (_, fname), fcfg in cfg_root.functioncfgs.items():
            blocks = get_all_blocks_filtered(fcfg)
            edges = sum(len(b.exits) for b in blocks)
            fn_stats.append({"function": fname, "blocks": len(blocks), "edges": edges})
        s.detail = f"{len(fn_stats)} function CFG(s) built"
        s.data = {
            "functions": fn_stats,
            "patches": ["visit_Try fix", "visit_Return phantom fix", "edge dedupe", "match desugar"],
        }

    # ------------------------------------------------------- 4 resource scan
    acquires: list[dict[str, Any]] = []
    with t.step("resources", "Scan for tracked acquire/release APIs") as s:
        seen = set()
        for node in ast.walk(tree):
            acq = _get_acquire_info(node, config.resources)
            if acq:
                var, acq_name, rel_name = acq
                key = (var, node.lineno)
                if key in seen:
                    continue
                seen.add(key)
                acquires.append({
                    "var": var,
                    "acquire": acq_name,
                    "release": rel_name,
                    "line": node.lineno,
                })
        s.detail = f"{len(acquires)} acquire point(s)" if acquires else "no tracked resources acquired"
        s.data = {"acquires": acquires}

    # --------------------------------------------- 4.5 interprocedural pass
    with t.step("interproc", "Parameter-effects analysis (helper(f) semantics)") as s:
        from .interproc import compute_param_effects
        effects = compute_param_effects(cfg_root)
        summarized = {}
        for fn, info in effects.items():
            interesting = {p: e for p, e in info["effects"].items() if e != "unknown"}
            if interesting:
                summarized[fn] = interesting
        s.detail = (
            f"{len(summarized)} helper(s) with releasable/escaping/leaking parameters"
            if summarized else "no helpers that affect resource lifetime"
        )
        s.data = {"functions": summarized}

    # ------------------------------------------------------- 5 path analysis
    leaks: list[Leak] = []
    with t.step("paths", "Path-sensitive liveness analysis (DFS with alias tracking)") as s:
        leaks, cfg_root = analyze_source_with_cfg(source, filename=filename, config=config)
        per_acquire = []
        for lk in leaks:
            if lk.kind in ("path", "path+exception"):
                per_acquire.append({
                    "var": lk.var,
                    "line": lk.acquire_line,
                    "verdict": "LEAK",
                    "leakingPaths": len(lk.paths),
                    "safePaths": len(lk.safe_paths),
                    "leakingPath": (lk.path_sources[0] if lk.path_sources else None),
                })
        s.detail = (
            f"{len(per_acquire)} definite leak(s) on control-flow paths"
            if per_acquire else "all acquires closed on every path"
        )
        s.data = {"acquiresAnalyzed": len(acquires), "findings": per_acquire}

    # ----------------------------------------------------- 6 exception pass
    exc_count = sum(1 for lk in leaks if "exception" in lk.kind)
    with t.step("exceptions", "Exception-safety pass (may-throw calls)") as s:
        flagged = [
            {"var": lk.var, "line": lk.acquire_line, "note": lk.exception_note}
            for lk in leaks if "exception" in lk.kind
        ]
        s.detail = f"{exc_count} acquires not exception-safe" if exc_count else "all acquires exception-safe"
        s.data = {"flagged": flagged}

    # ---------------------------------------------------------------- 7 fix
    fix_result: dict[str, Any] | None = None
    if fix and leaks:
        with t.step("fix", "Generate autofix (LibCST with-transform)") as s:
            from .fix import fix_source
            from libcst.codemod import diff_code
            original = source
            fixed = fix_source(original, leaks, config)
            if fixed != original:
                try:
                    diff = diff_code(original, fixed, 3)
                except Exception:
                    diff = ""
                s.detail = "fix generated — comments & formatting preserved"
                s.data = {"diff": diff}
                fix_result = {"applied": True, "code": fixed, "diff": diff}
            else:
                s.status = "warn"
                s.detail = "no automatic fix available for this pattern"
                s.data = {"reason": "unsupported pattern"}
                fix_result = {"applied": False}
    elif fix:
        fix_result = {"applied": False, "reason": "no leaks to fix"}

    # ------------------------------------------------------------ artifacts
    ast_tree = ast_to_json(tree) if tree is not None else None
    cfg_funcs = cfg_to_json(cfg_root, leaks) if cfg_root is not None else []

    # ------------------------------------------------------------- ensemble
    ensemble_result: dict[str, Any] | None = None
    if ensemble:
        with t.step("ensemble", "Ensemble: ruff pre-filter + CodeGate CFG verification") as s:
            from .ensemble import run_ensemble
            ensemble_result = run_ensemble(source, filename=filename, config=config)
            c = ensemble_result["counts"]
            s.detail = (
                f"{len(ensemble_result['verified'])} finding(s) verified: "
                f"{c['confirmed_path_leak']} confirmed, "
                f"{c['confirmed_exception_unsafe']} exception-unsafe, "
                f"{c['refuted_safe']} refuted"
            )
            s.data = ensemble_result

    total_ms = (time.perf_counter() - t0) * 1000

    return {
        "ok": True,
        "filename": filename,
        "summary": {
            "leakCount": len(leaks),
            "pathLeaks": sum(1 for lk in leaks if lk.kind in ("path", "path+exception")),
            "exceptionLeaks": exc_count,
            "acquires": len(acquires),
            "functionsAnalyzed": len(cfg_funcs),
            "analysisMs": round(total_ms, 2),
            "trajectorySteps": len(t),
        },
        "leaks": leaks_to_json(leaks),
        "trajectory": t.to_list(),
        "ast": ast_tree,
        "cfg": {"functions": cfg_funcs},
        "fix": fix_result,
        "ensemble": ensemble_result,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="codegate-webapi", description="CodeGate JSON API (one-shot)")
    parser.add_argument("file", help="Python file to analyze, or '-' for stdin")
    parser.add_argument("--fix", action="store_true", help="Include autofix preview")
    parser.add_argument("--ensemble", action="store_true", help="Include ruff+CodeGate ensemble verification")
    parser.add_argument("--filename", default=None, help="Display filename")
    args = parser.parse_args(argv)

    try:
        if args.file == "-":
            source = sys.stdin.read()
            filename = args.filename or "<stdin>"
        else:
            with open(args.file, encoding="utf-8", errors="replace") as f:
                source = f.read()
            filename = args.filename or args.file
        result = analyze_full(source, filename=filename, fix=args.fix,
                              ensemble=args.ensemble)
    except SyntaxError as e:
        result = {
            "ok": False,
            "error": f"SyntaxError: {e.msg}",
            "line": e.lineno,
            "filename": getattr(args, "filename", None) or getattr(args, "file", "unknown"),
        }
    except Exception as e:  # noqa: BLE001
        result = {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "filename": getattr(args, "filename", None) or getattr(args, "file", "unknown"),
        }

    try:
        json_output = json.dumps(result, indent=2, ensure_ascii=False)
        sys.stdout.write(json_output + "\n")
    except Exception as e:
        safe_result = {
            "ok": False,
            "error": f"JSON Serialization Error: {e}",
            "filename": getattr(args, "filename", None) or getattr(args, "file", "unknown"),
        }
        sys.stdout.write(json.dumps(safe_result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
