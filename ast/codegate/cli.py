"""CodeGate CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import analyze_file, analyze_source
from .config import CodeGateConfig
from .fix import fix_file, fix_source
from .report import format_json, format_text


def _collect_py_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))
        else:
            # glob pattern?
            files.extend([Path(x) for x in Path(".").glob(t) if Path(x).suffix == ".py"])
    # dedup
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codegate", description="CodeGate: Python resource-leak detector")
    parser.add_argument("targets", nargs="+", help="Python files or directories to analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--fix", action="store_true", help="Autofix leaks in place (with -> with)")
    parser.add_argument("--fix-dry", action="store_true", help="Show fixed code without writing")
    parser.add_argument("--fix-out", type=str, default=None, help="Write fixed files to this directory (mirror)")
    parser.add_argument("--config", type=str, default=None, help="Config JSON file (optional)")
    parser.add_argument("--quiet", action="store_true", help="Only exit code")

    args = parser.parse_args(argv)

    # Windows consoles default to cp1252, which cannot encode the report
    # glyphs; force UTF-8 so the CI gate does not die writing its own output.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    config = CodeGateConfig.default()
    if args.config:
        import json
        d = json.loads(Path(args.config).read_text())
        from .config import load_config_from_dict
        config = load_config_from_dict(d)

    files = _collect_py_files(args.targets)
    if not files:
        print("No Python files found.", file=sys.stderr)
        return 1

    all_leaks = []
    any_error = False

    for f in files:
        try:
            leaks = analyze_file(f, config)
        except SyntaxError as e:
            print(f"{f}: SyntaxError {e}", file=sys.stderr)
            any_error = True
            continue
        except Exception as e:
            import traceback
            print(f"{f}: analysis failed: {e}", file=sys.stderr)
            traceback.print_exc()
            any_error = True
            continue

        all_leaks.extend(leaks)

        if not args.quiet and not args.json:
            if leaks:
                print(format_text(leaks))
            else:
                print(f"{f}: ✓ no leaks")

        if leaks and args.fix:
            fixed = fix_file(f, leaks, config, in_place=True)
            if not args.quiet:
                print(f"  → fixed {f}")
        elif leaks and args.fix_dry:
            src = f.read_text()
            fixed = fix_source(src, leaks, config)
            print(f"\n--- {f} (fixed) ---\n{fixed}\n--- end ---\n")
        elif leaks and args.fix_out:
            out_root = Path(args.fix_out)
            # Mirror path: fix_out / relative to first target dir? Simple: fix_out / basename
            if len(files) == 1 and Path(args.targets[0]).is_file():
                out_path = out_root / f.name
            else:
                # Try to preserve relative to CWD
                try:
                    rel = f.relative_to(Path.cwd())
                except ValueError:
                    rel = Path(f.name)
                out_path = out_root / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fixed = fix_source(f.read_text(), leaks, config)
            out_path.write_text(fixed, encoding="utf-8")
            if not args.quiet:
                print(f"  → wrote fixed {out_path}")

    if args.json:
        out = format_json(all_leaks)
        print(out)

    # Exit 1 if leaks found (CI gate)
    return 1 if all_leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
