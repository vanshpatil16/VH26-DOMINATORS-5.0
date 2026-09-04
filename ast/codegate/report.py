"""Reporting helpers for CodeGate."""

from __future__ import annotations

import json
from pathlib import Path

from .analyzer import Leak


def format_text(leaks: list[Leak]) -> str:
    if not leaks:
        return "✓ No resource leaks detected."
    lines = [f"✗ Found {len(leaks)} leak(s):", ""]
    for lk in leaks:
        lines.append(f"  {lk.file}:{lk.acquire_line} [{lk.func}] {lk.message}")
        lines.append(f"    var={lk.var}  acquire={lk.acquire}  release={lk.release}")
        if lk.paths:
            # show first leaking path
            lines.append(f"    leaking path blocks: {lk.paths[0]}")
        lines.append("")
    return "\n".join(lines)


def format_json(leaks: list[Leak]) -> str:
    return json.dumps([lk.to_dict() for lk in leaks], indent=2)


def write_report(leaks: list[Leak], out: Path | None = None, fmt: str = "text") -> str:
    text = format_json(leaks) if fmt == "json" else format_text(leaks)
    if out:
        Path(out).write_text(text, encoding="utf-8")
    return text
