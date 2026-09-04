"""CodeGate CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report
from .analyzer import analyze_file_with_cfg, analyze_source_with_cfg
from .config import CodeGateConfig
from .fix import fix_file, fix_source
from .report import Colors, format_all_cfgs, format_json, format_text, should_use_color


def _collect_py_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))
        else:
            files.extend([Path(x) for x in Path(".").glob(t) if Path(x).suffix == ".py"])
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="codegate", description="CodeGate: Python resource-leak detector")
    parser.add_argument("targets", nargs="+", help="Python files or directories to analyze")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--cfg", action="store_true", help="Display full Control Flow Graph (CFG) graph in terminal")
    parser.add_argument("--color", action="store_true", help="Force color output")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("--fix", action="store_true", help="Autofix leaks in place (with -> with)")
    parser.add_argument("--fix-dry", action="store_true", help="Show fixed code without writing")
    parser.add_argument("--fix-out", type=str, default=None, help="Write fixed files to this directory (mirror)")
    parser.add_argument("--config", type=str, default=None, help="Config JSON file (optional)")
    parser.add_argument("--quiet", action="store_true", help="Only exit code")

    args = parser.parse_args(argv)
    use_color = should_use_color(force_color=args.color, no_color=args.no_color)
    c = Colors if use_color else report._NoColors()

    config = CodeGateConfig.default()
    if args.config:
        import json
        d = json.loads(Path(args.config).read_text())
        from .config import load_config_from_dict
        config = load_config_from_dict(d)

    files = _collect_py_files(args.targets)
    if not files:
        print(f"{c.RED}No Python files found.{c.RESET}", file=sys.stderr)
        return 1

    all_leaks = []
    any_error = False

    for f in files:
        try:
            leaks, cfg_root = analyze_file_with_cfg(f, config)
        except SyntaxError as e:
            print(f"{c.RED}{f}: SyntaxError {e}{c.RESET}", file=sys.stderr)
            any_error = True
            continue
        except Exception as e:
            import traceback
            print(f"{c.RED}{f}: analysis failed: {e}{c.RESET}", file=sys.stderr)
            traceback.print_exc()
            any_error = True
            continue

        all_leaks.extend(leaks)

        if not args.quiet and not args.json:
            # Print CFG graph if requested
            if args.cfg:
                print(format_all_cfgs(cfg_root, file_path=str(f), leaks=leaks, use_color=use_color))

            if leaks:
                print(format_text(leaks, use_color=use_color))
            else:
                print(f"{c.BOLD}{c.CYAN}{f}{c.RESET}: {c.GREEN}✓ no leaks{c.RESET}")

        if leaks and args.fix:
            fixed = fix_file(f, leaks, config, in_place=True)
            if not args.quiet:
                print(f"  {c.GREEN}→ fixed {f}{c.RESET}")
        elif leaks and args.fix_dry:
            src = f.read_text()
            fixed = fix_source(src, leaks, config)
            print(f"\n{c.CYAN}--- {f} (fixed) ---{c.RESET}\n{fixed}\n{c.CYAN}--- end ---{c.RESET}\n")
        elif leaks and args.fix_out:
            out_root = Path(args.fix_out)
            if len(files) == 1 and Path(args.targets[0]).is_file():
                out_path = out_root / f.name
            else:
                try:
                    rel = f.relative_to(Path.cwd())
                except ValueError:
                    rel = Path(f.name)
                out_path = out_root / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fixed = fix_source(f.read_text(), leaks, config)
            out_path.write_text(fixed, encoding="utf-8")
            if not args.quiet:
                print(f"  {c.GREEN}→ wrote fixed {out_path}{c.RESET}")

    if args.json:
        out = format_json(all_leaks)
        print(out)

    return 1 if all_leaks else 0


if __name__ == "__main__":
    raise SystemExit(main())

