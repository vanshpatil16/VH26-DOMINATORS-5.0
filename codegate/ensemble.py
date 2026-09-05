"""Ensemble mode — Semgrep + ruff as pre-filters, CodeGate as verifier.

Pipeline:
    1. Pre-filters (cheap, recall-oriented):
       - semgrep: CodeGate ruleset — deep metavariable/pattern matching across
         ALL tracked resource types (db, sockets, http clients, processes,
         files), including aliased imports
       - ruff: SIM115 + bandit-style S rules (style-level checks)
       - built-in syntactic scout: config-driven fallback for custom resources
    2. For each finding, run CodeGate CFG dataflow on that acquire:
         - path leak at line          -> CONFIRMED (with path evidence)
         - exception-unsafe at line   -> CONFIRMED_EXCEPTION (upgraded severity)
         - acquire analyzed, all paths closed + exception-safe -> REFUTED (suppress noise)
         - no tracked acquire at line -> UNVERIFIED

Output: JSON report merging all tools, deduplicated by line.

CLI:
    python -m codegate.ensemble file.py [--out report.json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .analyzer import analyze_source
from .config import CodeGateConfig

# ruff is a rust binary shipped by the `ruff` pip package.
# Bandit rules are S-prefixed in ruff (B106 -> S106).
_RUFF_SELECT = ["SIM115", "S110", "S113", "S106"]

# Semgrep ruleset shipped with CodeGate (deep pattern matching for all
# tracked resources, including aliased imports).
_SEMGREP_RULES = Path(__file__).parent / "semgrep" / "rules.yml"

# Prefer concrete rules over the loose aliased-connect rule when both hit one line
_SEMGREP_RULE_PRIORITY = [
    "codegate-unguarded-open",
    "codegate-unguarded-tempfile",
    "codegate-unguarded-socket",
    "codegate-unguarded-db-connect",
    "codegate-unguarded-http-client",
    "codegate-unguarded-process",
    "codegate-unguarded-aliased-connect",
]


def _ruff_binary() -> str | None:
    import shutil
    b = shutil.which("ruff")
    if b:
        return b
    # fall back to python -m ruff
    try:
        subprocess.run([sys.executable, "-m", "ruff", "--version"],
                       capture_output=True, timeout=15)
        return sys.executable + " -m ruff"
    except Exception:
        return None


def _semgrep_binary() -> str | None:
    import shutil
    b = shutil.which("semgrep")
    if b:
        return b
    try:
        proc = subprocess.run([sys.executable, "-m", "semgrep", "--version"],
                              capture_output=True, timeout=30)
        if proc.returncode == 0:
            return sys.executable + " -m semgrep"
        return None
    except Exception:
        return None


def run_semgrep(source: str, filename: str, timeout: int = 120) -> dict[str, Any]:
    """Run the CodeGate semgrep ruleset on the source.

    Semgrep is the DEEP pre-filter: metavariable/pattern matching across all
    tracked resource types, including aliased imports (the loose
    codegate-unguarded-aliased-connect rule). Findings are verified by the
    CodeGate CFG engine afterwards.

    Returns {'available': bool, 'findings': [...], 'note': str?}.
    """
    import shutil
    import tempfile

    if not _SEMGREP_RULES.exists():
        return {"available": False, "findings": [], "note": "ruleset missing"}
    binary = _semgrep_binary()
    if binary is None:
        return {"available": False, "findings": [],
                "note": "semgrep not installed (pip install semgrep)"}

    with tempfile.TemporaryDirectory(prefix="codegate-semgrep-") as td:
        target = Path(td) / Path(filename).name or "input.py"
        target.write_text(source, encoding="utf-8")
        argv = binary.split() + [
            "scan", "--config", str(_SEMGREP_RULES), "--json", str(target),
        ]
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return {"available": False, "findings": [], "note": f"semgrep failed: {e}"}

    try:
        data = json.loads(proc.stdout.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {"available": True, "findings": [], "note": "unparseable semgrep output"}

    def rule_rank(rule_id: str) -> int:
        short = rule_id.split(".")[-1]
        try:
            return _SEMGREP_RULE_PRIORITY.index(short)
        except ValueError:
            return len(_SEMGREP_RULE_PRIORITY)

    findings: list[dict[str, Any]] = []
    by_line: dict[int, dict[str, Any]] = {}
    for r in data.get("results", []):
        line = r.get("start", {}).get("line")
        rule = (r.get("check_id") or "").split(".")[-1]
        f = {
            "tool": "semgrep",
            "rule": rule,
            "line": line,
            "col": r.get("start", {}).get("col"),
            "message": r.get("extra", {}).get("message"),
            "name": rule,
        }
        if line is None:
            continue
        prev = by_line.get(line)
        if prev is None or rule_rank(rule) < rule_rank(prev["rule"]):
            by_line[line] = f

    findings = sorted(by_line.values(), key=lambda f: f["line"] or 0)
    return {"available": True, "findings": findings}


def run_ruff(source: str, filename: str, select: list[str] | None = None) -> dict[str, Any] | None:
    """Run ruff on source via stdin. Returns {'available': bool, 'findings': [...]}."""
    binary = _ruff_binary()
    if binary is None:
        return {"available": False, "findings": [], "note": "ruff not installed (pip install ruff)"}
    argv = binary.split() + ["check", "--output-format", "json"]
    argv += ["--select", ",".join(select or _RUFF_SELECT)]
    argv += ["--stdin-filename", filename, "-"]
    try:
        proc = subprocess.run(argv, input=source.encode("utf-8"),
                              capture_output=True, timeout=60)
        if proc.returncode == 2 and b"Unknown rule" in proc.stderr:
            # some selectors unsupported in this ruff version — retry with SIM115 only
            argv[argv.index("--select") + 1] = "SIM115"
            proc = subprocess.run(argv, input=source.encode("utf-8"),
                                  capture_output=True, timeout=60)
    except Exception as e:  # noqa: BLE001
        return {"available": False, "findings": [], "note": f"ruff failed: {e}"}
    try:
        raw = json.loads(proc.stdout.decode("utf-8") or "[]")
    except json.JSONDecodeError:
        return {"available": True, "findings": [], "note": "unparseable ruff output"}
    findings = [
        {
            "tool": "ruff",
            "rule": f.get("code"),
            "line": f.get("location", {}).get("row"),
            "col": f.get("location", {}).get("column"),
            "message": f.get("message"),
            "name": f.get("name"),
        }
        for f in raw
        if isinstance(f, dict)
    ]
    return {"available": True, "findings": findings}


def classify_with_codegate(
    ruff_findings: list[dict[str, Any]],
    leaks: list[Any],
) -> list[dict[str, Any]]:
    """Attach a CodeGate verdict to each ruff finding.

    leaks: list of analyzer.Leak objects (already computed on the same source).
    """
    # index codegate findings by acquire line
    by_line: dict[int, list[Any]] = {}
    for lk in leaks:
        by_line.setdefault(lk.acquire_line, []).append(lk)

    out = []
    for f in ruff_findings:
        line = f.get("line")
        verdict = "unverified"
        evidence: dict[str, Any] = {}
        matched = by_line.get(line, [])
        if matched:
            lk = matched[0]
            if lk.kind in ("path", "path+exception"):
                verdict = "confirmed_path_leak"
                evidence = {
                    "kind": lk.kind,
                    "var": lk.var,
                    "acquire": lk.acquire,
                    "leaking_path": (lk.path_sources[0] if lk.path_sources else None),
                    "exception_note": lk.exception_note,
                }
            elif lk.kind == "exception":
                verdict = "confirmed_exception_unsafe"
                evidence = {
                    "kind": lk.kind,
                    "var": lk.var,
                    "acquire": lk.acquire,
                    "note": lk.exception_note,
                }
        elif line in getattr(classify_with_codegate, "_analyzed_acquires", set()):
            verdict = "refuted_safe"
            evidence = {
                "note": "CodeGate proved cleanup is guaranteed on every path "
                        "(branches, aliases, exceptions) — suppress this finding"
            }
        out.append({**f, "verdict": verdict, "evidence": evidence})
    return out


def syntactic_prefilter(source: str, config: CodeGateConfig | None = None) -> list[dict[str, Any]]:
    """Cheap recall-oriented scan for tracked resources WITHOUT a with-guard.

    ruff's SIM115 only covers builtin open() — real production leaks use
    sqlite3.connect, psycopg2, requests.Session, Popen, etc. This scan emits
    pseudo-findings for any tracked acquire assigned to a local that has no
    syntactic with-guard anywhere on its statement path. Noisy by design —
    the CFG verifier (classify_with_codegate) decides the verdict.
    """
    import ast
    from .imports import build_import_map
    from .analyzer import _get_acquire_info

    if config is None:
        config = CodeGateConfig.default()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imap = build_import_map(tree)

    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        acq = _get_acquire_info(node, config.resources, imap)
        if not acq:
            continue
        var, canonical, rel = acq
        # find if this assign's enclosing scope guards it with `with <var>` later?
        # cheap check: is there ANY `with` statement in the same function whose
        # item references the var (with closing(var) / with var:)? Heuristic.
        guarded = False
        parent_fn: ast.AST | None = None
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(getattr(n, "lineno", -1) == node.lineno for n in ast.walk(fn)):
                    parent_fn = fn
                    break
        scope = parent_fn if parent_fn is not None else tree
        for w in ast.walk(scope):
            if isinstance(w, (ast.With, ast.AsyncWith)):
                for item in w.items:
                    ctx = item.context_expr
                    # with var: / with closing(var): / with var as x:
                    names: set[str] = set()
                    if isinstance(ctx, ast.Name):
                        names.add(ctx.id)
                    elif isinstance(ctx, ast.Call):
                        for a in ctx.args:
                            if isinstance(a, ast.Name):
                                names.add(a.id)
                    if var in names:
                        guarded = True
        if guarded:
            continue
        findings.append({
            "tool": "codegate-syntactic",
            "rule": f"codegate-unguarded-{canonical.split('.')[-1]}",
            "line": node.lineno,
            "col": getattr(node, "col_offset", 0) + 1,
            "message": f"'{var}' = {canonical}(...) acquired without a context manager",
            "name": "resource-without-context-manager",
        })
    return findings


def run_ensemble(source: str, filename: str = "input.py",
                 config: CodeGateConfig | None = None) -> dict[str, Any]:
    """Full ensemble run: ruff pre-filter -> CodeGate verify -> merged report."""
    if config is None:
        config = CodeGateConfig.default()

    # 1) pre-filters: semgrep (deep patterns) -> ruff (style) -> syntactic scout
    semgrep_result = run_semgrep(source, filename)
    ruff_result = run_ruff(source, filename)
    ruff_findings = ruff_result["findings"] if ruff_result else []
    syn_findings = syntactic_prefilter(source, config)

    # dedupe by line: semgrep wins (deepest), then ruff, then syntactic
    used_lines: set[int | None] = set()
    merged: list[dict[str, Any]] = []
    for f in (semgrep_result.get("findings", [])
              + ruff_findings + syn_findings):
        line = f.get("line")
        if line in used_lines:
            continue
        used_lines.add(line)
        merged.append(f)

    # 2) CodeGate deep analysis (independent of ruff)
    leaks = analyze_source(source, filename=filename, config=config)

    # expose which acquire lines CodeGate analyzed (for refutation)
    analyzed: set[int] = set()

    # recompute acquire lines the way the analyzer does
    import ast
    from .imports import build_import_map
    from .analyzer import _get_acquire_info, _walk_own
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    if tree is not None:
        imap = build_import_map(tree)
        for node in ast.walk(tree):
            acq = _get_acquire_info(node, config.resources, imap)
            if acq:
                analyzed.add(node.lineno)
    classify_with_codegate._analyzed_acquires = analyzed  # type: ignore[attr-defined]

    verified = classify_with_codegate(merged, leaks)

    counts = {
        "confirmed_path_leak": sum(1 for v in verified if v["verdict"] == "confirmed_path_leak"),
        "confirmed_exception_unsafe": sum(1 for v in verified if v["verdict"] == "confirmed_exception_unsafe"),
        "refuted_safe": sum(1 for v in verified if v["verdict"] == "refuted_safe"),
        "unverified": sum(1 for v in verified if v["verdict"] == "unverified"),
    }
    noise_reduction = 0
    if verified:
        noise_reduction = round(counts["refuted_safe"] / len(verified) * 100)

    return {
        "semgrep": semgrep_result,
        "ruff": ruff_result,
        "syntacticPrefilter": {"findings": len(syn_findings)},
        "codegate": {
            "leaks": [lk.to_dict() for lk in leaks],
            "analyzedAcquireLines": sorted(analyzed),
        },
        "verified": verified,
        "counts": counts,
        "noiseReductionPct": noise_reduction,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codegate-ensemble",
                                     description="ruff SIM115 pre-filter + CodeGate path-sensitive verifier")
    parser.add_argument("file", help="Python file to analyze")
    parser.add_argument("--out", default=None, help="Write JSON report to file")
    args = parser.parse_args(argv)

    src = Path(args.file).read_text(encoding="utf-8")
    report = run_ensemble(src, filename=args.file)

    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"report written to {args.out}")
    else:
        print(text)

    # exit 1 if any confirmed leak
    return 1 if report["counts"]["confirmed_path_leak"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
