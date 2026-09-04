"""CodeGate CI — preventive pipeline for commits and GitHub Actions.

Two entry points (wired into the main CLI):

    codegate ci <targets> [--changed-only] [--base REF] [--ensemble]
        Scans files, prints a human summary, emits GitHub annotations
        (::error / ::warning) so findings show inline on PRs, exits 1 on leaks.

    codegate install-hook
        Writes a git pre-commit hook that runs `codegate ci` on staged .py
        files — blocks `git commit` when leaks exist.

Annotation escaping follows GitHub Commands rules (% and \n escaped).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .analyzer import analyze_file
from .config import CodeGateConfig


def _gh_escape(text: str) -> str:
    """GitHub annotation payloads escape %, \r and \n."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _annotation(level: str, file: str, line: int, title: str, message: str) -> str:
    return f"::{level} file={file},line={line},title={_gh_escape(title)}::{_gh_escape(message)}"


def changed_python_files(base: str | None = None) -> list[Path]:
    """Python files changed vs a git ref (defaults to uncommitted + HEAD diff)."""
    if base is None:
        # uncommitted changes (staged + unstaged)
        argv = ["git", "diff", "--name-only", "--diff-filter=ACM", "HEAD"]
    else:
        argv = ["git", "diff", "--name-only", "--diff-filter=ACM", base]
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        files = [Path(l) for l in out.stdout.splitlines() if l.strip().endswith(".py")]
        # on first commit HEAD may not exist — fall back to staged only
        if not files and base is None:
            out = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACM", "--cached"],
                capture_output=True, text=True, timeout=30)
            files = [Path(l) for l in out.stdout.splitlines() if l.strip().endswith(".py")]
        return [f for f in files if f.exists()]
    except Exception:
        return []


def collect_targets(targets: list[str]) -> list[Path]:
    from .cli import _collect_py_files
    return _collect_py_files(targets)


def run_ci(targets: list[str], ensemble: bool = False, changed_only: bool = False,
           base: str | None = None, quiet: bool = False,
           emit_annotations: bool = True) -> int:
    from .ensemble import run_ensemble

    if changed_only:
        files = changed_python_files(base)
        if not files:
            if not quiet:
                print("CodeGate: no changed Python files to scan.")
            return 0
    else:
        files = collect_targets(targets)
        if not files:
            if not quiet:
                print("CodeGate: no Python files found.", file=sys.stderr)
            return 1

    config = CodeGateConfig.default()
    total_path_leaks = 0
    total_exception = 0
    annotations: list[str] = []
    summary_rows: list[tuple[str, int, str]] = []

    for f in files:
        try:
            leaks = analyze_file(f, config)
        except SyntaxError as e:
            annotations.append(_annotation("error", str(f), e.lineno or 1,
                                           "SyntaxError", e.msg))
            total_path_leaks += 1
            continue
        except Exception as e:  # noqa: BLE001
            if not quiet:
                print(f"CodeGate: analysis failed for {f}: {e}", file=sys.stderr)
            continue

        for lk in leaks:
            if lk.kind in ("path", "path+exception"):
                level = "error"
                total_path_leaks += 1
            else:
                level = "warning"
                total_exception += 1
            title = f"CodeGate: resource leak in {lk.func}()"
            annotations.append(_annotation(level, str(f), lk.acquire_line, title, lk.message))

            if lk.exception_note:
                annotations.append(_annotation("warning", str(f), lk.acquire_line,
                                               f"CodeGate: exception risk in {lk.func}()",
                                               lk.exception_note))
            summary_rows.append((str(f), lk.acquire_line, lk.message))

        if ensemble:
            src = Path(f).read_text(encoding="utf-8")
            ens = run_ensemble(src, filename=str(f), config=config)
            if not quiet:
                c = ens["counts"]
                print(f"  ensemble[{f}]: {c['confirmed_path_leak']} confirmed · "
                      f"{c['confirmed_exception_unsafe']} exception-unsafe · "
                      f"{c['refuted_safe']} refuted (noise −{ens['noiseReductionPct']}%)")

    if not quiet:
        print(f"\nCodeGate CI — scanned {len(files)} file(s)")
        for row in summary_rows:
            print(f"  ✗ {row[0]}:{row[1]} {row[2]}")
        status = "PASSED" if total_path_leaks == 0 else "FAILED"
        print(f"  {status}: {total_path_leaks} path leak(s), {total_exception} exception risk(s)")

    # GitHub annotations go to stdout (Actions picks these up)
    if emit_annotations:
        for a in annotations:
            print(a)

    return 1 if total_path_leaks > 0 else 0


PRE_COMMIT_HOOK = """#!/bin/sh
# CodeGate pre-commit hook — blocks commits containing resource leaks.
# Installed by: codegate install-hook
staged_py=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.py$')
if [ -n "$staged_py" ]; then
    echo "CodeGate: scanning staged Python files..."
    if command -v python >/dev/null 2>&1; then PY=python; else PY=python3; fi
    $PY -m codegate.ci $staged_py --hook
    status=$?
    if [ $status -ne 0 ]; then
        echo ""
        echo "✗ CodeGate found resource leaks — commit blocked."
        echo "  Fix the leaks above (or use 'git commit --no-verify' to skip)."
        exit 1
    fi
    echo "✓ CodeGate: no leaks in staged files."
fi
exit 0
"""


def install_hook() -> int:
    """Install the pre-commit hook into the current git repository."""
    try:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        print("Not inside a git repository.", file=sys.stderr)
        return 1
    if not root:
        print("Not inside a git repository.", file=sys.stderr)
        return 1
    hooks_dir = Path(root) / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if "codegate.ci" in existing:
            print("CodeGate pre-commit hook already installed.")
            return 0
        # preserve existing hook by chaining
        backup = hook_path.with_suffix(".pre-codegate.bak")
        backup.write_text(existing, encoding="utf-8")
        print(f"Existing pre-commit hook backed up to {backup.name}")

    hook_path.write_text(PRE_COMMIT_HOOK, encoding="utf-8")
    try:
        hook_path.chmod(0o755)
    except Exception:
        pass  # Windows: git-bash executes hooks regardless of POSIX bits
    print(f"✓ Installed CodeGate pre-commit hook at {hook_path}")
    print("  Now `git commit` scans staged .py files and blocks on leaks.")
    print("  Remove with: rm .git/hooks/pre-commit  (or --no-verify to bypass once)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codegate ci",
                                     description="Preventive CI: scan code, emit GitHub annotations, exit 1 on leaks")
    parser.add_argument("targets", nargs="*", default=["."], help="Files/dirs to scan (default: .)")
    parser.add_argument("--changed-only", action="store_true",
                        help="Scan only files changed vs git (PR-friendly)")
    parser.add_argument("--base", default=None, help="Git ref to diff against (with --changed-only)")
    parser.add_argument("--ensemble", action="store_true", help="Include ruff+CodeGate ensemble verification")
    parser.add_argument("--quiet", action="store_true", help="Suppress human summary (annotations still emitted)")
    parser.add_argument("--hook", action="store_true",
                        help=argparse.SUPPRESS)  # pre-commit hook mode: human output, no annotations
    args = parser.parse_args(argv)

    if args.hook:
        return run_ci(args.targets, ensemble=False, changed_only=False,
                      quiet=False, emit_annotations=False)

    return run_ci(
        args.targets,
        ensemble=args.ensemble,
        changed_only=args.changed_only,
        base=args.base,
        quiet=args.quiet,
        emit_annotations=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
