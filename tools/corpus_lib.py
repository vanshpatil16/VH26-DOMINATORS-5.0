"""Shared plumbing for building the LeakGuard corpus.

Design rules for the whole dataset pipeline:

* **Deterministic.** No timestamps, no wall-clock, no unseeded randomness.
  Rebuilding the dataset from a clean checkout produces byte-identical files.
* **Provenance-first.** Every sample carries where it came from and, for a
  mutant, exactly which line the mutation broke. That line *is* the label.
* **Grouped.** Every sample carries a `family`. Splits are made by family, never
  by file, because near-duplicate code across a train/test boundary is the
  single easiest way to report a fake F1.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, "dataset")
REAL_DIR = os.path.join(DATASET, "real_code")
MUTATED_DIR = os.path.join(DATASET, "mutated_code")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

#: Inline marker that flags the acquisition line of a deliberate leak.
#: Comments never reach the analyser (it is pure AST), so this is safe to embed.
LEAK_MARKER = "leakguard: expect-leak"
SAFE_MARKER = "leakguard: expect-safe"
UNKNOWN_MARKER = "leakguard: expect-unknown"


@dataclass
class Sample:
    """One corpus file plus everything needed to train and evaluate on it."""

    sample_id: str
    path: str                       # POSIX, repo-relative
    folder: str                     # real_code | mutated_code
    origin: str                     # handwritten | synthesized | generated
    family: str                     # grouping key for the split
    label: int                      # 0 = correct handling, 1 = contains a leak
    operator: Optional[str] = None  # mutation operator id, generated samples only
    derived_from: Optional[str] = None
    edge_cases: List[str] = field(default_factory=list)
    expected_leak_lines: List[int] = field(default_factory=list)
    expected_unknown_lines: List[int] = field(default_factory=list)
    resource_types: List[str] = field(default_factory=list)
    note: str = ""
    source_sha1: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def sha1_of(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def to_posix(path: str) -> str:
    return path.replace(os.sep, "/")


def rel(path: str) -> str:
    return to_posix(os.path.relpath(path, ROOT))


def marker_lines(source: str, marker: str) -> List[int]:
    """1-based line numbers carrying an inline expectation marker."""
    return [
        index
        for index, line in enumerate(source.splitlines(), start=1)
        if marker in line
    ]


def strip_markers(source: str) -> str:
    """Remove expectation markers, keeping the rest of the comment intact."""
    pattern = re.compile(r"\s*#\s*leakguard: expect-(?:leak|safe|unknown)[^\n]*")
    return pattern.sub("", source)


def normalise(source: str) -> str:
    """Canonical form for dedup: parse and unparse, discarding formatting."""
    try:
        return ast.unparse(ast.parse(source))
    except SyntaxError:
        return source


def write_sample(abs_path: str, source: str, *, keep_markers: bool = True) -> str:
    """Write a corpus file with LF endings and return the text written."""
    ensure_dir(os.path.dirname(abs_path))
    text = source if keep_markers else strip_markers(source)
    if not text.endswith("\n"):
        text += "\n"
    with open(abs_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return text


def write_manifest(path: str, samples: Iterable[Sample]) -> int:
    ensure_dir(os.path.dirname(path))
    count = 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for sample in sorted(samples, key=lambda s: s.sample_id):
            handle.write(sample.to_json() + "\n")
            count += 1
    return count


def read_manifest(path: str) -> List[Sample]:
    if not os.path.exists(path):
        return []
    out: List[Sample] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                out.append(Sample(**json.loads(line)))
    return out


def resource_types_in(source: str) -> List[str]:
    """Registry types acquired by a source file, for manifest bookkeeping."""
    from leakguard.detector import analyse_module  # local import keeps tools light

    analysis = analyse_module(source, "<manifest>")
    return sorted({site.resource_type for site in analysis.sites})


def parses(source: str) -> bool:
    try:
        ast.parse(source)
        return True
    except SyntaxError:
        return False


def dedupe_key(source: str) -> str:
    """MinHash is overkill at this corpus size; canonical-AST sha1 is enough."""
    return sha1_of(normalise(strip_markers(source)))


def iter_python_files(root: str) -> Iterable[str]:
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def build_sample(
    *,
    sample_id: str,
    abs_path: str,
    folder: str,
    origin: str,
    family: str,
    label: int,
    source: str,
    operator: Optional[str] = None,
    derived_from: Optional[str] = None,
    edge_cases: Optional[Sequence[str]] = None,
    note: str = "",
    explicit_leak_lines: Optional[Sequence[int]] = None,
) -> Sample:
    """Write the file and assemble its manifest record in one step."""
    text = write_sample(abs_path, source)
    leak_lines = (
        list(explicit_leak_lines)
        if explicit_leak_lines is not None
        else marker_lines(text, LEAK_MARKER)
    )
    return Sample(
        sample_id=sample_id,
        path=rel(abs_path),
        folder=folder,
        origin=origin,
        family=family,
        label=label,
        operator=operator,
        derived_from=derived_from,
        edge_cases=list(edge_cases or []),
        expected_leak_lines=sorted(leak_lines),
        expected_unknown_lines=sorted(marker_lines(text, UNKNOWN_MARKER)),
        resource_types=resource_types_in(text),
        note=note,
        source_sha1=sha1_of(text),
    )


def summarise(samples: Sequence[Sample]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for sample in samples:
        counts["total"] = counts.get("total", 0) + 1
        key_label = "label_%d" % sample.label
        counts[key_label] = counts.get(key_label, 0) + 1
        if sample.operator:
            key = "op_" + sample.operator
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
