"""Friendly terminal reporting for CodeGate.

Design goals:
- Show only what matters (leaking function's CFG by default)
- Human-readable paths:  open(path) → f.read() → return None
- if/else tree graph instead of raw block/edge dumps
- Clear fix suggestion
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Optional

from .analyzer import Leak
from .scalpel_patch import get_all_blocks_filtered


class Colors:
    """ANSI color codes for terminal highlighting."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


class _NoColors:
    RESET = BOLD = DIM = RED = GREEN = YELLOW = BLUE = ""
    MAGENTA = CYAN = WHITE = GRAY = ""


def should_use_color(force_color: bool = False, no_color: bool = False) -> bool:
    if no_color:
        return False
    if force_color:
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _stmt_src(stmt: ast.AST) -> str:
    try:
        return ast.unparse(stmt)
    except Exception:
        return str(stmt)


def _short(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _path_summary(stmts: list[str], max_items: int = 5, item_w: int = 34) -> str:
    """open(path) → f.read() → return None   (compact arrow summary)"""
    if not stmts:
        return ""
    parts = [_short(s.splitlines()[0], item_w) for s in stmts[:max_items]]
    if len(stmts) > max_items:
        parts.append("…")
    return " → ".join(parts)


def _branch_labels(exits) -> list[Optional[str]]:
    """Label each exit edge as TRUE/FALSE when complementary, else the condition."""
    if len(exits) == 2:
        a, b = exits
        if a.exitcase is not None and b.exitcase is not None:
            try:
                ta, tb = ast.unparse(a.exitcase), ast.unparse(b.exitcase)
            except Exception:
                ta = tb = ""
            neg_a = tb == f"not {ta}" or tb == f"not ({ta})"
            neg_b = ta == f"not {tb}" or ta == f"not ({tb})"
            if neg_a:
                return ["TRUE", "FALSE"]
            if neg_b:
                return ["FALSE", "TRUE"]
    labels: list[Optional[str]] = []
    for e in exits:
        ec = e.exitcase
        if ec is None:
            labels.append(None)
        elif isinstance(ec, ast.Constant):
            labels.append("TRUE" if ec.value else "FALSE")
        else:
            try:
                labels.append("if " + ast.unparse(ec))
            except Exception:
                labels.append(None)
    return labels


# ---------------------------------------------------------------------------
# friendly leak report
# ---------------------------------------------------------------------------

def format_text(leaks: list[Leak], use_color: bool = True) -> str:
    c = Colors if use_color else _NoColors()
    if not leaks:
        return f"{c.BOLD}{c.GREEN}✓ No resource leaks detected.{c.RESET}"

    lines = [
        "",
        f"{c.BOLD}{c.RED}{'█'*3} CODEGATE FOUND {len(leaks)} LEAK{'S' if len(leaks)>1 else ''} {'█'*3}{c.RESET}",
        "",
    ]
    for lk in leaks:
        title = "DEFINITE RESOURCE LEAK" if lk.confidence == "definite" else "POTENTIAL RESOURCE LEAK"
        lines.append(f"{c.BOLD}{c.RED}┌─ 🔴 {title}{c.RESET}  {c.BOLD}{lk.file}:{lk.acquire_line}{c.RESET}"
                     f" {c.GRAY}· in {lk.func}() · {lk.rule} · {lk.resource_type}{c.RESET}")
        lines.append(f"{c.RED}│{c.RESET}")
        lines.append(f"{c.RED}│{c.RESET}  {c.BOLD}'{lk.var}' = {lk.acquire}(...){c.RESET}"
                     f" {c.GRAY}— is not guaranteed to be {lk.release}()'d{c.RESET}")
        if lk.leak_reasons:
            lines.append(f"{c.RED}│{c.RESET}  {c.GRAY}leak paths: {c.RESET}"
                         + ", ".join(f"{c.RED}{r}{c.RESET}" for r in lk.leak_reasons))

        # leaking path (statement-level summary)
        if lk.path_sources:
            for srcs in lk.path_sources[:1]:
                lines.append(f"{c.RED}│{c.RESET}  {c.RED}✗ leaking path:{c.RESET}  {_path_summary(srcs)}")
                lines.append(f"{c.RED}│{c.RESET}                      {c.GRAY}└─ '{lk.var}' never closed here{c.RESET}")
        # safe path for contrast
        if lk.safe_path_sources:
            for srcs in lk.safe_path_sources[:1]:
                lines.append(f"{c.RED}│{c.RESET}  {c.GREEN}✓ safe path:    {c.RESET}  {_path_summary(srcs)}")

        if lk.exception_note:
            lines.append(f"{c.RED}│{c.RESET}  {c.YELLOW}⚠ {lk.exception_note}{c.RESET}")

        lines.append(f"{c.RED}│{c.RESET}")
        lines.append(
            f"{c.RED}│{c.RESET}  {c.BOLD}{c.GREEN}💡 FIX:{c.RESET} use a context manager, or close on every branch:\n"
            f"{c.RED}│{c.RESET}       with {lk.acquire}(...) as {lk.var}:{c.GRAY}   # closes automatically{c.RESET}\n"
            f"{c.RED}│{c.RESET}           ...{c.GRAY}   # or: try/finally with {lk.var}.{lk.release}(){c.RESET}"
        )
        lines.append(f"{c.RED}└{'─'*60}{c.RESET}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# if/else tree CFG renderer
# ---------------------------------------------------------------------------

def format_cfg(
    fcfg,
    func_name: str = "<main>",
    file_path: str = "",
    leaks: Optional[list[Leak]] = None,
    use_color: bool = True,
) -> str:
    """Render the CFG as an if/else tree humans can read at a glance.

    Example:
        ●─ [3] line 4  ← LEAK: exits without closing 'f'
        │     f = open(path)
        │     data = f.read()
        │     ├── TRUE ─ [4] line 9  ← LEAK
        │     │     return None
        │     └── FALSE ─ [5] line 11  ✓ closed
    """
    c = Colors if use_color else _NoColors()
    blocks = get_all_blocks_filtered(fcfg)
    if not blocks:
        return f"{c.GRAY}(empty CFG for {func_name}){c.RESET}"

    entry = fcfg.entryblock if fcfg.entryblock in blocks else blocks[0]
    leaking_ids: set[int] = set()
    safe_ids: set[int] = set()
    for lk in (leaks or []):
        for p in lk.paths:
            leaking_ids.update(p)
        for p in lk.safe_paths:
            safe_ids.update(p)

    out: list[str] = []
    visited: set[int] = set()

    def render(block, prefix: str, header: str, is_last: bool):
        visited.add(block.id)
        body_prefix = prefix + ("│   " if not is_last else "    ") if prefix else "    "

        # header
        at = block.at()
        loc = f"line {at}" if at else "entry"
        if block.id in leaking_ids:
            tag = f"  {c.BOLD}{c.RED}← LEAK: exits without closing{c.RESET}"
        elif block.id in safe_ids:
            tag = f"  {c.GREEN}✓ resource closed{c.RESET}"
        elif block is entry:
            tag = f"  {c.CYAN}(start){c.RESET}"
        else:
            tag = ""
        out.append(f"{prefix}{header}{c.BOLD}{c.YELLOW}[{block.id}]{c.RESET} {c.GRAY}{loc}{c.RESET}{tag}")

        # statements
        for s in block.statements:
            src = _short(_stmt_src(s).splitlines()[0], 68)
            marker = f" {c.RED}🔴{c.RESET}" if block.id in leaking_ids else (
                     f" {c.GREEN}🟢{c.RESET}" if block.id in safe_ids else "")
            out.append(f"{body_prefix}{c.CYAN}{src}{c.RESET}{marker}")

        exits = block.exits
        labels = _branch_labels(exits)
        if not exits:
            out.append(f"{body_prefix}{c.WHITE}└─ EXIT{c.RESET}")
            return
        for i, e in enumerate(exits):
            last = i == len(exits) - 1
            econn = "└─ " if last else "├─ "
            lbl = labels[i]
            if e.target.id in visited:
                arrow = f"{lbl} ─► " if lbl else "──► "
                out.append(f"{body_prefix}{econn}{c.BOLD}{c.MAGENTA}{arrow}{c.RESET}"
                           f"{c.YELLOW}back to Block {e.target.id} (loop){c.RESET}")
                continue
            # merge branch label into the child's header connector
            if lbl:
                child_header = f"{econn}{c.BOLD}{c.MAGENTA}{lbl}{c.RESET} ─ "
            else:
                child_header = econn
            render(e.target, body_prefix, child_header, last)

    # header
    params = ""
    for s in entry.statements:
        if isinstance(s, ast.FunctionDef):
            params = _sig(s)
            break
    title = f"{func_name}({params})" if func_name != "<module>" else "<module level>"
    out.append("")
    out.append(f"{c.BOLD}{c.CYAN}  ▼ Control flow of {title}{c.RESET} {c.GRAY}({file_path}){c.RESET}")
    out.append(f"{c.GRAY}  {'─'*60}{c.RESET}")
    render(entry, "  ", "●─ ", True)
    out.append("")
    return "\n".join(out)


def _sig(fn: ast.FunctionDef) -> str:
    try:
        args = ast.unparse(fn.args)
    except Exception:
        args = ""
    return args


def format_all_cfgs(
    cfg_root,
    file_path: str = "",
    leaks: Optional[list[Leak]] = None,
    use_color: bool = True,
    only_leaking: bool = False,
) -> str:
    """Render CFGs. By default only functions involved in leaks (less noise)."""
    leak_funcs = {lk.func for lk in (leaks or [])} if only_leaking else None
    out: list[str] = []
    if hasattr(cfg_root, "functioncfgs") and cfg_root.functioncfgs:
        for (_, func_name), fcfg in cfg_root.functioncfgs.items():
            if leak_funcs is not None and func_name not in leak_funcs:
                continue
            out.append(format_cfg(fcfg, func_name=func_name, file_path=file_path,
                                  leaks=leaks, use_color=use_color))
    elif cfg_root.entryblock is not None:
        out.append(format_cfg(cfg_root, func_name="<module>", file_path=file_path,
                              leaks=leaks, use_color=use_color))
    return "\n".join(out)


def format_json(leaks: list[Leak]) -> str:
    return json.dumps([lk.to_dict() for lk in leaks], indent=2)


def write_report(leaks: list[Leak], out: Path | None = None, fmt: str = "text", use_color: bool = False) -> str:
    text = format_json(leaks) if fmt == "json" else format_text(leaks, use_color=use_color)
    if out:
        Path(out).write_text(text, encoding="utf-8")
    return text
