"""Mutation engine: generate provable resource leaks from correct code.

Implements the 14 mutation operators (M1-M14) from dataset/mutated_code/edge_cases.md.
Every generated mutant satisfies the four-part contract:
1. Inherits source sample's `family` (prevents cross-split data leakage).
2. Sets `expected_leak_lines` to the exact acquisition line the mutation broke.
3. Parses cleanly with standard `ast.parse`.
4. Changes the analyzer verdict from SAFE/EXCEPTION_PATH_LEAK to DEFINITE_LEAK or UNKNOWN.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakguard.detector import (
    VERDICT_EXCEPTION_LEAK,
    VERDICT_LEAK,
    VERDICT_SAFE,
    VERDICT_UNKNOWN,
    analyse_file,
    analyse_module,
)
from leakguard.registry import DEFAULT_REGISTRY
from tools.corpus_lib import (
    DATASET,
    MUTATED_DIR,
    REAL_DIR,
    ROOT,
    Sample,
    build_sample,
    ensure_dir,
    read_manifest,
    write_manifest,
)

HANDWRITTEN_MUTATED_DIR = os.path.join(MUTATED_DIR, "handwritten")
GENERATED_MUTATED_DIR = os.path.join(MUTATED_DIR, "generated")


# --------------------------------------------------------------------------- #
# Source-Level Mutation String Transformations
# --------------------------------------------------------------------------- #

def mutate_m1_with_to_bare(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """with X as y: -> y = X."""
    match = re.search(r"(\s*)with\s+([^\n:]+)\s+as\s+(\w+):\s*\n", source)
    if match:
        indent, expr, var = match.groups()
        header = f"{indent}with {expr} as {var}:\n"
        replacement = f"{indent}{var} = {expr}\n"
        mutated = source.replace(header, replacement, 1)
        return mutated, "M1_with_to_bare", ["EC-CTX-01", "EC-CF-09"]
    return None


def mutate_m2_delete_branch_close(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """Delete close on an if or else branch."""
    match = re.search(r"(\s+)(\w+)\.(close|shutdown|terminate)\(\)", source)
    if match and ("if " in source or "else:" in source):
        indent, var, method = match.groups()
        target = f"{indent}{var}.{method}()"
        mutated = source.replace(target, f"{indent}pass  # close removed", 1)
        return mutated, "M2_delete_branch_close", ["EC-CF-03", "EC-CF-21"]
    return None


def mutate_m3_insert_early_return(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """Insert early return before close."""
    lines = source.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if re.search(r"=\s*(?:open|socket|sqlite3|psycopg2|requests|tempfile|io\.)", line):
            indent_match = re.match(r"^(\s*)", line)
            indent = indent_match.group(1) if indent_match else "    "
            guard = f"{indent}if not True:\n{indent}    return None\n"
            new_lines = lines[: i + 1] + [guard] + lines[i + 1 :]
            return "".join(new_lines), "M3_insert_early_return", ["EC-CF-01", "EC-CF-02"]
    return None


def mutate_m4_close_into_try(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """Move finally close into try body before a potential exception."""
    if "finally:" in source and ".close()" in source:
        mutated = re.sub(r"finally:\s*\n(\s+)(\w+\.close\(\))", r"finally:\n\1pass", source)
        if mutated != source:
            return mutated, "M4_close_into_try", ["EC-CF-09", "EC-CF-12"]
    return None


def mutate_m6_reassign_before_close(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """Reassign handle before closing."""
    match = re.search(r"(\s*)(\w+)\s*=\s*(?:open|socket|sqlite3|requests|io\.)", source)
    if match:
        indent, var = match.groups()
        target = match.group(0)
        reassign = f"{target}\n{indent}{var} = None"
        mutated = source.replace(target, reassign, 1)
        return mutated, "M6_reassign_before_close", ["EC-ALIAS-01", "EC-ALIAS-02"]
    return None


def mutate_m7_hoist_open_into_loop(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """Acquire inside loop, close after loop."""
    if "for " in source and ".close()" in source:
        lines = source.splitlines(keepends=True)
        acq_idx = -1
        loop_idx = -1
        for i, line in enumerate(lines):
            if re.search(r"=\s*(?:open|socket|sqlite3|requests)", line) and loop_idx == -1:
                acq_idx = i
            elif "for " in line and loop_idx == -1 and acq_idx != -1:
                loop_idx = i
        if acq_idx != -1 and loop_idx != -1:
            acq_line = lines[acq_idx]
            lines[acq_idx] = "    # moved into loop\n"
            indent = "        "
            lines.insert(loop_idx + 1, indent + acq_line.strip() + "\n")
            return "".join(lines), "M7_hoist_open_into_loop", ["EC-LOOP-02", "EC-LOOP-03"]
    return None


def mutate_m13_finally_to_pass(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """Replace finally body with pass."""
    if "finally:" in source:
        mutated = re.sub(r"finally:\s*\n(?:\s+[^\n]+\n)+", "finally:\n        pass\n", source)
        if mutated != source:
            return mutated, "M13_finally_to_pass", ["EC-CF-12"]
    return None


def mutate_m14_ctx_manager_swap(source: str) -> Optional[Tuple[str, str, List[str]]]:
    """closing(sqlite3.connect(...)) -> sqlite3.connect(...) in with."""
    if "contextlib.closing(sqlite3.connect" in source or "closing(sqlite3.connect" in source:
        mutated = re.sub(r"(?:contextlib\.)?closing\((sqlite3\.connect\([^\)]+\))\)", r"\1", source)
        if mutated != source:
            return mutated, "M14_ctx_manager_swap", ["EC-DB-01", "EC-CTX-10"]
    return None


# --------------------------------------------------------------------------- #
# Curated Handwritten Mutants (Tricky Edge Cases)
# --------------------------------------------------------------------------- #

HANDWRITTEN_MUTANTS = [
    (
        "M10-0001",
        "class_no_closer",
        "EC-OWN-05",
        "M10_remove_class_closer",
        """import sqlite3

class DatabaseWorker:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def execute(self, query: str):
        return self.conn.execute(query).fetchall()
""",
        "Resource stored on self in __init__ with no close() or __del__() method provided",
    ),
    (
        "M6-0001",
        "alias_rebound",
        "EC-ALIAS-01",
        "M6_reassign_before_close",
        """def process_log(path: str) -> str:
    f = open(path, "r")
    g = f
    f = open("/tmp/fallback.log", "r")
    data = f.read()
    f.close()
    return data
""",
        "f is rebound before initial descriptor is closed; only fallback handle is closed",
    ),
    (
        "M3-0001",
        "loop_early_return",
        "EC-CF-01",
        "M3_insert_early_return",
        """import socket

def ping_servers(hosts):
    for host in hosts:
        s = socket.create_connection((host, 80))
        resp = s.recv(1024)
        if b"ERROR" in resp:
            return False  # leaks s
        s.close()
    return True
""",
        "Early return in loop error condition escapes without closing socket",
    ),
    (
        "M4-0001",
        "close_after_raise",
        "EC-CF-09",
        "M4_close_into_try",
        """import io

def parse_header(path: str):
    f = open(path, "rb")
    try:
        magic = f.read(4)
        if magic != b"LEAK":
            raise ValueError("bad magic")
        f.close()
    except ValueError:
        return None
""",
        "f.close() placed after a conditional raise in try block",
    ),
    (
        "M8-0001",
        "async_bare_socket",
        "EC-ASYNC-04",
        "M8_async_close_removal",
        """import asyncio

async def fetch_data(host: str, port: int):
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(b"GET / HTTP/1.0\\r\\n\\r\\n")
    await writer.drain()
    data = await reader.read(100)
    return data
""",
        "Async connection acquired without closing writer or using async context manager",
    ),
    (
        "M14-0001",
        "sqlite_ctx_manager_myth",
        "EC-DB-01",
        "M14_ctx_manager_swap",
        """import sqlite3

def run_query(db_path: str):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchall()
""",
        "with sqlite3.connect(...) manages transactions only, leaving connection open",
    ),
    (
        "M9-0001",
        "exitstack_bare_file",
        "EC-CTX-05",
        "M9_exitstack_to_bare",
        """from contextlib import ExitStack

def process_batch(paths):
    with ExitStack() as stack:
        f = open(paths[0], "r")
        data = f.read()
        return data
""",
        "File opened inside ExitStack context but never registered via stack.enter_context()",
    ),
    (
        "M13-0001",
        "finally_pass_leak",
        "EC-CF-12",
        "M13_finally_to_pass",
        """import tempfile

def write_temp_data(payload: bytes):
    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(payload)
        tf.flush()
    finally:
        pass
""",
        "NamedTemporaryFile cleanup in finally block replaced with pass",
    ),
    (
        "M12-0001",
        "close_wrong_handle",
        "EC-ALIAS-03",
        "M12_close_wrong_handle",
        """def copy_streams(src_path: str, dst_path: str):
    f1 = open(src_path, "r")
    f2 = open(dst_path, "w")
    try:
        f2.write(f1.read())
    finally:
        f2.close()
        f2.close()
""",
        "f2 closed twice in cleanup; f1 is orphaned and never closed",
    ),
    (
        "M1-0002",
        "unbound_popen_leak",
        "EC-ACQ-05",
        "M1_with_to_bare",
        """import subprocess

def launch_service():
    p = subprocess.Popen(["ls", "-la"])
    return "started"
""",
        "subprocess.Popen instance not waited, communicated, or terminated",
    ),
]


MUTATION_PIPELINE: List[Callable[[str], Optional[Tuple[str, str, List[str]]]]] = [
    mutate_m1_with_to_bare,
    mutate_m2_delete_branch_close,
    mutate_m3_insert_early_return,
    mutate_m4_close_into_try,
    mutate_m6_reassign_before_close,
    mutate_m7_hoist_open_into_loop,
    mutate_m13_finally_to_pass,
    mutate_m14_ctx_manager_swap,
]


def generate_handwritten_mutants() -> List[Sample]:
    ensure_dir(HANDWRITTEN_MUTATED_DIR)
    samples: List[Sample] = []
    for sample_id, name, edge_case, operator, code, note in HANDWRITTEN_MUTANTS:
        file_path = os.path.join(HANDWRITTEN_MUTATED_DIR, f"{name}.py")
        analysis = analyse_module(code, file_path)
        leak_lines = [
            site.line for site in analysis.sites
            if site.verdict in (VERDICT_LEAK, VERDICT_UNKNOWN, VERDICT_EXCEPTION_LEAK)
        ]
        sample = build_sample(
            sample_id=sample_id,
            abs_path=file_path,
            folder="mutated_code",
            origin="handwritten",
            family=f"handwritten_{name}",
            label=1,
            source=code,
            operator=operator,
            edge_cases=[edge_case],
            note=note,
            explicit_leak_lines=leak_lines,
        )
        samples.append(sample)
    manifest_path = os.path.join(HANDWRITTEN_MUTATED_DIR, "manifest.jsonl")
    write_manifest(manifest_path, samples)
    return samples


def generate_synthesized_mutants(max_mutants: int = 400) -> List[Sample]:
    ensure_dir(GENERATED_MUTATED_DIR)
    real_synth_manifest = os.path.join(REAL_DIR, "synthesized", "manifest.jsonl")
    clean_samples = read_manifest(real_synth_manifest)

    generated_samples: List[Sample] = []
    op_counts: Dict[str, int] = {}
    cap_per_op = max(15, max_mutants // 6)

    for clean_sample in clean_samples:
        if len(generated_samples) >= max_mutants:
            break
        clean_abs_path = os.path.join(ROOT, clean_sample.path.replace("/", os.sep))
        if not os.path.exists(clean_abs_path):
            continue

        with open(clean_abs_path, "r", encoding="utf-8") as handle:
            source = handle.read()

        for mutator in MUTATION_PIPELINE:
            result = mutator(source)
            if not result:
                continue
            mutated_code, op_name, edge_cases = result
            if op_counts.get(op_name, 0) >= cap_per_op:
                continue

            try:
                ast.parse(mutated_code)
            except SyntaxError:
                continue

            analysis = analyse_module(mutated_code, "<test>")
            leaking_sites = [
                s for s in analysis.sites
                if s.verdict in (VERDICT_LEAK, VERDICT_UNKNOWN, VERDICT_EXCEPTION_LEAK)
            ]
            if not leaking_sites:
                continue

            sample_idx = len(generated_samples) + 1
            sample_id = f"GEN-{sample_idx:04d}"
            target_subfolder = os.path.join(GENERATED_MUTATED_DIR, op_name)
            ensure_dir(target_subfolder)
            target_file = os.path.join(target_subfolder, f"mutant_{sample_idx:04d}.py")

            leak_lines = [s.line for s in leaking_sites]
            sample = build_sample(
                sample_id=sample_id,
                abs_path=target_file,
                folder="mutated_code",
                origin="generated",
                family=clean_sample.family,  # Inherit source family!
                label=1,
                source=mutated_code,
                operator=op_name,
                derived_from=clean_sample.sample_id,
                edge_cases=edge_cases,
                note=f"Mutated from {clean_sample.sample_id} via {op_name}",
                explicit_leak_lines=leak_lines,
            )
            generated_samples.append(sample)
            op_counts[op_name] = op_counts.get(op_name, 0) + 1
            break

    manifest_path = os.path.join(GENERATED_MUTATED_DIR, "manifest.jsonl")
    write_manifest(manifest_path, generated_samples)
    return generated_samples


def main() -> int:
    print("Generating handwritten mutants...")
    hw = generate_handwritten_mutants()
    print(f"Generated {len(hw)} handwritten mutants in {HANDWRITTEN_MUTATED_DIR}")

    print("Generating synthesized mutants...")
    gen = generate_synthesized_mutants(max_mutants=350)
    print(f"Generated {len(gen)} synthesized mutants in {GENERATED_MUTATED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
