"""Command-line interface for LeakGuard static resource leak analyzer.

Usage:
    python -m leakguard scan <paths...> [options]

Options:
    --sarif <file>        Write SARIF v2.1.0 report for GitHub Code Scanning
    --json                Output results as JSON
    --explain             Show detailed Explainable AI (XAI) log-odds feature attributions
    --diff                Show unified diff for automated fix suggestions
    --fix                 Apply automated fixes in-place
    --fail-on-warning     Fail build (exit 1) on warnings (e.g. exception-path leaks)
    --quiet               Only print findings and summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional, Sequence

from .fixer import generate_diff, suggest_fix_for_source
from .sarif import write_sarif
from .scoring import ScoredSite, score_module

# ANSI terminal colors (graceful fallback on non-tty)
USE_COLOR = sys.stdout.isatty() and os.name != "nt" or "TERM" in os.environ


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


RED = "31;1"
YELLOW = "33;1"
GREEN = "32;1"
CYAN = "36;1"
BOLD = "1"
DIM = "2"


def print_site_report(site_score: ScoredSite, source_lines: List[str], explain: bool = True) -> None:
    site = site_score.site
    v = site_score.final_verdict

    if v == "DEFINITE_LEAK":
        badge = _c(RED, "[DEFINITE LEAK]")
    elif v == "LIKELY_LEAK":
        badge = _c(RED, "[LIKELY LEAK]")
    elif v == "POSSIBLE_LEAK":
        badge = _c(YELLOW, "[WARNING: POSSIBLE LEAK]")
    else:
        badge = _c(GREEN, "[SAFE]")

    print(f"\n{badge} {_c(BOLD, f'{site_score.filename}:{site.line}')} - Handle '{_c(CYAN, site.handle)}' ({site.resource_type})")
    print(f"  Acquisition: `{site.call}` | P(leak): {_c(BOLD, f'{site_score.p_leak:.1%}')} | Risk: {_c(BOLD, f'{site_score.risk:.2f}')} (Exposure: {site_score.exposure:.1f})")

    # Show code snippet around acquisition
    if 1 <= site.line <= len(source_lines):
        start = max(1, site.line - 1)
        end = min(len(source_lines), site.line + 2)
        for ln in range(start, end + 1):
            prefix = " >" if ln == site.line else "  "
            print(f"  {_c(DIM, f'{prefix} {ln:4d} |')} {source_lines[ln - 1]}")

    # Evidence points
    if site_score.evidence_lines:
        print(f"  {_c(BOLD, 'Evidence:')}")
        for ev in site_score.evidence_lines:
            print(f"    * {ev}")

    # Explainable AI Feature Attribution Breakdown
    if explain and site_score.attributions:
        print(f"  {_c(BOLD, 'Explainable AI Feature Contributions (Log-Odds Impact):')}")
        for attr in site_score.attributions:
            if abs(attr.contribution) < 0.005:
                continue
            sign = "+" if attr.contribution > 0 else ""
            color = RED if attr.contribution > 0 else GREEN
            print(f"    * {attr.description:55s} : {_c(color, f'{sign}{attr.contribution:+.2f}')} (val={attr.value})")

    # Counterfactual Impact
    if site_score.is_blocking or site_score.final_verdict == "POSSIBLE_LEAK":
        print(f"  {_c(BOLD, 'Remediation & Counterfactual Analysis:')}")
        print(f"    * {site_score.fix_suggestion}")
        reduction = (site_score.risk - site_score.counterfactual_risk) / max(0.001, site_score.risk)
        print(f"    * Counterfactual: If refactored, Risk drops to {_c(GREEN, f'{site_score.counterfactual_risk:.2f}')} ({reduction:.1%} reduction -> SAFE)")


def collect_python_files(paths: Sequence[str]) -> List[str]:
    files: List[str] = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".py"):
            files.append(p)
        elif os.path.isdir(p):
            for dirpath, _, filenames in os.walk(p):
                for f in sorted(filenames):
                    if f.endswith(".py"):
                        files.append(os.path.join(dirpath, f))
    return sorted(files)


def scan_files(
    files: Sequence[str],
    explain: bool = True,
    show_diff: bool = False,
    apply_fixes: bool = False,
    fail_on_warning: bool = False,
    sarif_output: Optional[str] = None,
    json_output: bool = False,
) -> int:
    all_scored_sites: List[ScoredSite] = []
    blocking_count = 0
    warning_count = 0
    safe_count = 0

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                source = handle.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
            continue

        scored = score_module(source, file_path)
        all_scored_sites.extend(scored)

        lines = source.splitlines()
        for site_score in scored:
            if site_score.is_blocking:
                blocking_count += 1
            elif site_score.final_verdict == "POSSIBLE_LEAK":
                warning_count += 1
            else:
                safe_count += 1

            if not json_output and site_score.final_verdict != "SAFE":
                print_site_report(site_score, lines, explain=explain)

                if show_diff or apply_fixes:
                    fixed_code = suggest_fix_for_source(
                        source, site_score.site.line, site_score.site.handle, site_score.site.call
                    )
                    if fixed_code and fixed_code != source:
                        diff = generate_diff(file_path, source, fixed_code)
                        print(f"  {_c(BOLD, 'Proposed Fix Diff:')}\n{diff}")
                        if apply_fixes:
                            with open(file_path, "w", encoding="utf-8") as handle:
                                handle.write(fixed_code)
                            print(f"  {_c(GREEN, 'Applied automated fix to ' + file_path)}")

    if sarif_output:
        write_sarif(sarif_output, all_scored_sites, root_dir=os.getcwd())
        print(f"\nWrote SARIF report to {_c(CYAN, sarif_output)}")

    if json_output:
        payload = [
            {
                "file": s.filename,
                "line": s.site.line,
                "handle": s.site.handle,
                "call": s.site.call,
                "resource_type": s.site.resource_type,
                "rule_verdict": s.rule_verdict,
                "final_verdict": s.final_verdict,
                "p_leak": s.p_leak,
                "risk": s.risk,
                "exposure": s.exposure,
                "blocking": s.is_blocking,
                "evidence": s.evidence_lines,
                "fix": s.fix_suggestion,
                "attributions": [
                    {"feature": a.feature_name, "contribution": a.contribution, "desc": a.description}
                    for a in s.attributions
                ],
            }
            for s in all_scored_sites
        ]
        print(json.dumps(payload, indent=2))
        return 1 if (blocking_count > 0 or (fail_on_warning and warning_count > 0)) else 0

    # Summary
    print(f"\n{_c(BOLD, 'LeakGuard Scan Summary')}")
    print(f"  Files scanned : {len(files)}")
    print(f"  Sites tracked : {len(all_scored_sites)}")
    print(f"  Blocking leaks: {_c(RED if blocking_count else GREEN, str(blocking_count))}")
    print(f"  Warnings      : {_c(YELLOW if warning_count else GREEN, str(warning_count))}")
    print(f"  Safe sites    : {_c(GREEN, str(safe_count))}")

    if blocking_count > 0:
        print(f"\n{_c(RED, 'FAIL:')} {blocking_count} blocking resource leak(s) detected.")
        return 1
    elif fail_on_warning and warning_count > 0:
        print(f"\n{_c(YELLOW, 'FAIL:')} {warning_count} warning(s) treated as build failures (--fail-on-warning).")
        return 1
    else:
        print(f"\n{_c(GREEN, 'SUCCESS:')} Build passed clean.")
        return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="leakguard",
        description="LeakGuard: Path-Aware Static Resource Leak Analyzer for Python",
    )
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan Python files for resource leaks")
    scan_parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    scan_parser.add_argument("--sarif", help="Output SARIF v2.1.0 file path")
    scan_parser.add_argument("--json", action="store_true", help="Output JSON results")
    scan_parser.add_argument("--no-explain", dest="explain", action="store_false", help="Hide XAI feature breakdown")
    scan_parser.add_argument("--diff", action="store_true", help="Show unified diff of proposed fixes")
    scan_parser.add_argument("--fix", action="store_true", help="Apply proposed fixes in-place")
    scan_parser.add_argument("--fail-on-warning", action="store_true", help="Fail build on warnings")

    args = parser.parse_args(argv)

    if not args.command or args.command == "scan":
        paths = getattr(args, "paths", [])
        if not paths:
            scan_parser.print_help()
            return 1
        files = collect_python_files(paths)
        if not files:
            print("No Python files found.")
            return 0
        return scan_files(
            files,
            explain=getattr(args, "explain", True),
            show_diff=getattr(args, "diff", False),
            apply_fixes=getattr(args, "fix", False),
            fail_on_warning=getattr(args, "fail_on_warning", False),
            sarif_output=getattr(args, "sarif", None),
            json_output=getattr(args, "json", False),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
