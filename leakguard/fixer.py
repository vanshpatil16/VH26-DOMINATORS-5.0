"""Automated fix generator and unified diff patcher for LeakGuard.

Transforms leaked resource acquisitions into safe structured cleanup:
1. Single functions with `f = open(...)` -> `with open(...) as f:`
2. Non-context-manager handles -> `try: ... finally: <var>.close()`
3. SQLite connections -> `with contextlib.closing(sqlite3.connect(...)) as conn:`
4. Provides unified diff output (`generate_diff`) and in-place rewriting (`apply_fix`).
"""

from __future__ import annotations

import difflib
import os
import re
from typing import Dict, List, Optional, Tuple

from .scoring import ScoredSite


def suggest_fix_for_source(source: str, site_line: int, handle: str, call: str) -> Optional[str]:
    """Generate a refactored version of source fixing the leak on site_line."""
    lines = source.splitlines(keepends=True)
    if site_line < 1 or site_line > len(lines):
        return None

    target_line_idx = site_line - 1
    target_line = lines[target_line_idx]

    # Pattern: var = open(...)
    match_assign = re.match(r"^(\s*)(\w+)\s*=\s*(open|io\.open|codecs\.open)\((.*)\)\s*$", target_line)
    if match_assign:
        indent, var, func_name, args = match_assign.groups()
        # Find closing statement if it exists below
        close_pattern = re.compile(rf"^\s*{re.escape(var)}\.close\(\)\s*$")
        new_lines: List[str] = []

        for i, line in enumerate(lines):
            if i == target_line_idx:
                new_lines.append(f"{indent}with {func_name}({args}) as {var}:\n")
            elif i > target_line_idx:
                # If this line is the old close call, omit it
                if close_pattern.match(line):
                    continue
                # Indent lines inside the function after open by 4 spaces
                if line.strip():
                    new_lines.append(f"    {line}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        return "".join(new_lines)

    # Pattern: generic acquire var = call(...)
    match_generic = re.match(r"^(\s*)(\w+)\s*=\s*([^\n]+)\s*$", target_line)
    if match_generic:
        indent, var, expr = match_generic.groups()
        # Check if close is sqlite3 -> with closing(...)
        if "sqlite3.connect" in expr:
            new_lines = []
            has_closing_import = "closing" in source
            if not has_closing_import:
                new_lines.append("from contextlib import closing\n")
            for i, line in enumerate(lines):
                if i == target_line_idx:
                    new_lines.append(f"{indent}with closing({expr}) as {var}:\n")
                elif i > target_line_idx:
                    if re.match(rf"^\s*{re.escape(var)}\.close\(\)\s*$", line):
                        continue
                    new_lines.append(f"    {line}" if line.strip() else line)
                else:
                    new_lines.append(line)
            return "".join(new_lines)
        else:
            # Wrap in try / finally block
            new_lines = []
            for i, line in enumerate(lines):
                if i == target_line_idx:
                    new_lines.append(line)
                    new_lines.append(f"{indent}try:\n")
                elif i > target_line_idx:
                    if re.match(rf"^\s*{re.escape(var)}\.close\(\)\s*$", line):
                        continue
                    new_lines.append(f"    {line}" if line.strip() else line)
                else:
                    new_lines.append(line)
            new_lines.append(f"{indent}finally:\n")
            new_lines.append(f"{indent}    {var}.close()\n")
            return "".join(new_lines)

    return None


def generate_diff(filename: str, original: str, fixed: str) -> str:
    """Produce a standard unified diff string between original and fixed source."""
    orig_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        fixed_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=os.linesep if hasattr(os, "linesep") else "\n",
    )
    return "".join(diff)
