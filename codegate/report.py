"""Reporting and CFG visualization helpers for CodeGate."""

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
    UNDERLINE = "\033[4m"

    # Standard colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Backgrounds
    BG_RED = "\033[41m\033[97m"
    BG_GREEN = "\033[42m\033[30m"
    BG_CYAN = "\033[46m\033[30m"


def should_use_color(force_color: bool = False, no_color: bool = False) -> bool:
    if no_color:
        return False
    if force_color:
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def format_text(leaks: list[Leak], use_color: bool = True) -> str:
    """Format leak findings into a colorized human-readable terminal report."""
    c = Colors if use_color else _NoColors()
    if not leaks:
        return f"{c.BOLD}{c.GREEN}✓ No resource leaks detected.{c.RESET}"

    lines = [
        f"{c.BOLD}{c.RED}✗ Found {len(leaks)} resource leak(s):{c.RESET}",
        f"{c.GRAY}{'─' * 60}{c.RESET}",
    ]

    for i, lk in enumerate(leaks, 1):
        lines.append(
            f" {c.BOLD}{c.WHITE}[{i}]{c.RESET} {c.BOLD}{c.CYAN}{lk.file}:{lk.acquire_line}{c.RESET} "
            f"in {c.BOLD}{c.MAGENTA}{lk.func}(){c.RESET}"
        )
        lines.append(f"     {c.RED}🚨 {lk.message}{c.RESET}")
        lines.append(
            f"     {c.GRAY}Resource:{c.RESET} {c.BOLD}{c.YELLOW}var={lk.var}{c.RESET}  "
            f"{c.GRAY}Acquire:{c.RESET} {c.CYAN}{lk.acquire}(){c.RESET}  "
            f"{c.GRAY}Release:{c.RESET} {c.GREEN}{lk.release}(){c.RESET}"
        )

        if lk.paths:
            lines.append(f"     {c.BOLD}{c.RED}Leaking Path(s):{c.RESET}")
            for path in lk.paths:
                path_str = " ──► ".join(f"Block {b}" for b in path)
                lines.append(f"       • {c.RED}{path_str}{c.RESET}")

        if lk.safe_paths:
            lines.append(f"     {c.BOLD}{c.GREEN}Safe Path(s):{c.RESET}")
            for path in lk.safe_paths:
                path_str = " ──► ".join(f"Block {b}" for b in path)
                lines.append(f"       • {c.GREEN}{path_str}{c.RESET}")

        lines.append(f"{c.GRAY}{'─' * 60}{c.RESET}")

    return "\n".join(lines)


def format_cfg(
    fcfg,
    func_name: str = "<main>",
    file_path: str = "",
    leaks: Optional[list[Leak]] = None,
    use_color: bool = True,
) -> str:
    """Format a single function CFG graph into a visual ASCII/ANSI tree representation."""
    c = Colors if use_color else _NoColors()
    blocks = get_all_blocks_filtered(fcfg)
    if not blocks:
        return f"{c.GRAY}(Empty CFG for {func_name}){c.RESET}"

    # Collect leaking & safe block IDs for highlighting
    leaking_blocks: set[int] = set()
    safe_blocks: set[int] = set()
    if leaks:
        for lk in leaks:
            if lk.func == func_name or func_name == "<module>":
                for path in lk.paths:
                    leaking_blocks.update(path)
                for path in lk.safe_paths:
                    safe_blocks.update(path)

    header = f" FUNCTION CFG: {func_name}() [{file_path}] "
    box_width = max(len(header) + 4, 64)
    lines = [
        "",
        f"{c.BOLD}{c.CYAN}┌{'─' * box_width}┐{c.RESET}",
        f"{c.BOLD}{c.CYAN}│ {header.ljust(box_width - 2)} │{c.RESET}",
        f"{c.BOLD}{c.CYAN}└{'─' * box_width}┘{c.RESET}",
    ]

    for b in blocks:
        block_id = b.id
        line_no = b.at()
        line_str = f"Line {line_no}" if line_no else "Entry/Exit"

        # Highlight tag
        if block_id in leaking_blocks:
            tag = f" {c.BOLD}{c.RED}🔴 [LEAKING PATH]{c.RESET}"
            block_color = c.RED
        elif block_id in safe_blocks:
            tag = f" {c.BOLD}{c.GREEN}🟢 [SAFE PATH]{c.RESET}"
            block_color = c.GREEN
        elif b is fcfg.entryblock:
            tag = f" {c.BOLD}{c.CYAN}🚀 [ENTRY]{c.RESET}"
            block_color = c.CYAN
        else:
            tag = ""
            block_color = c.YELLOW

        lines.append(f"{c.GRAY}  │{c.RESET}")
        lines.append(
            f"{c.GRAY}  ├─►{c.RESET} {c.BOLD}{block_color}[Block {block_id}]{c.RESET} "
            f"{c.GRAY}({line_str}){c.RESET}{tag}"
        )

        # Render statements inside block
        if b.statements:
            lines.append(f"{c.GRAY}  │   │  {c.DIM}Statements:{c.RESET}")
            for idx, stmt in enumerate(b.statements, 1):
                try:
                    stmt_code = ast.unparse(stmt).splitlines()[0]
                except Exception:
                    stmt_code = str(stmt)
                if len(stmt_code) > 70:
                    stmt_code = stmt_code[:67] + "..."
                lines.append(
                    f"{c.GRAY}  │   │    {idx}.{c.RESET} {c.CYAN}{stmt_code}{c.RESET}"
                )

        # Render exits / edges
        if b.exits:
            lines.append(f"{c.GRAY}  │   │  {c.DIM}Exits:{c.RESET}")
            for link in b.exits:
                target_id = link.target.id
                cond_str = ""
                if link.exitcase is not None:
                    try:
                        cond_code = ast.unparse(link.exitcase)
                    except Exception:
                        cond_code = str(link.exitcase)
                    cond_str = f" {c.GRAY}[Condition: {c.MAGENTA}{cond_code}{c.GRAY}]{c.RESET}"
                else:
                    cond_str = f" {c.GRAY}[Unconditional]{c.RESET}"

                target_tag = ""
                if target_id in leaking_blocks:
                    target_tag = f" {c.RED}🔴{c.RESET}"
                elif target_id in safe_blocks:
                    target_tag = f" {c.GREEN}🟢{c.RESET}"

                lines.append(
                    f"{c.GRAY}  │   └───►{c.RESET} {c.BOLD}{c.YELLOW}Block {target_id}{c.RESET}{cond_str}{target_tag}"
                )
        else:
            lines.append(
                f"{c.GRAY}  │   └───►{c.RESET} {c.BOLD}{c.WHITE}(Return / Exit){c.RESET}"
            )

    lines.append(f"{c.GRAY}  └{'─' * (box_width - 2)}{c.RESET}\n")
    return "\n".join(lines)


def format_all_cfgs(
    cfg_root,
    file_path: str = "",
    leaks: Optional[list[Leak]] = None,
    use_color: bool = True,
) -> str:
    """Format all function CFGs in a root CFG module into string representation."""
    out: list[str] = []
    if hasattr(cfg_root, "functioncfgs") and cfg_root.functioncfgs:
        for (_, func_name), fcfg in cfg_root.functioncfgs.items():
            out.append(format_cfg(fcfg, func_name=func_name, file_path=file_path, leaks=leaks, use_color=use_color))
    elif cfg_root.entryblock:
        out.append(format_cfg(cfg_root, func_name="<module>", file_path=file_path, leaks=leaks, use_color=use_color))
    return "\n".join(out)


def format_json(leaks: list[Leak]) -> str:
    return json.dumps([lk.to_dict() for lk in leaks], indent=2)


def write_report(leaks: list[Leak], out: Path | None = None, fmt: str = "text", use_color: bool = False) -> str:
    text = format_json(leaks) if fmt == "json" else format_text(leaks, use_color=use_color)
    if out:
        Path(out).write_text(text, encoding="utf-8")
    return text


class _NoColors:
    """Fallback when colors are disabled."""
    RESET = ""
    BOLD = ""
    DIM = ""
    UNDERLINE = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    GRAY = ""
    BG_RED = ""
    BG_GREEN = ""
    BG_CYAN = ""

