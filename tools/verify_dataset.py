"""Verify the corpus against its own labels — run this before every training run.

Three classes of problem it catches:

1. **Broken samples.** A file that no longer parses, or a manifest row pointing
   at a file whose sha1 has drifted.
2. **False positives.** Any `DEFINITE_LEAK` on a label-0 sample. This number is
   the honest precision signal, and it is the one that decides whether a team
   keeps the tool switched on.
3. **False negatives.** A label-1 sample whose marked leak line the analyser
   does not flag.

`EXCEPTION_PATH_LEAK` on a label-0 sample is reported but is **not** an error:
the shape genuinely leaks if the body raises, which is why it has its own
warning tier. Those samples are the most valuable hard negatives in the corpus.

Exit code is 1 when a hard problem is found, so this can gate CI.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakguard.detector import (  # noqa: E402
    VERDICT_EXCEPTION_LEAK,
    VERDICT_LEAK,
    VERDICT_UNKNOWN,
    analyse_file,
)
from tools.corpus_lib import (  # noqa: E402
    DATASET,
    ROOT,
    Sample,
    iter_python_files,
    read_manifest,
    sha1_of,
)

MANIFESTS = (
    "real_code/handwritten/manifest.jsonl",
    "real_code/synthesized/manifest.jsonl",
    "real_code/escapes/manifest.jsonl",
    "mutated_code/handwritten/manifest.jsonl",
    "mutated_code/generated/manifest.jsonl",
)


def load_all() -> List[Sample]:
    samples: List[Sample] = []
    for name in MANIFESTS:
        samples.extend(read_manifest(os.path.join(DATASET, name)))
    return samples


def verify(samples: List[Sample], strict_sha: bool = True) -> Tuple[List[str], Dict[str, int]]:
    errors: List[str] = []
    stats: collections.Counter = collections.Counter()

    for sample in samples:
        abs_path = os.path.join(ROOT, sample.path.replace("/", os.sep))
        if not os.path.exists(abs_path):
            errors.append("MISSING FILE       %s" % sample.path)
            continue
        with open(abs_path, "r", encoding="utf-8") as handle:
            text = handle.read()
        if strict_sha and sample.source_sha1 and sha1_of(text) != sample.source_sha1:
            errors.append("SHA DRIFT          %s" % sample.path)

        analysis = analyse_file(abs_path)
        if analysis.parse_error:
            errors.append("PARSE ERROR        %s: %s" % (sample.path, analysis.parse_error))
            continue

        stats["sites"] += len(analysis.sites)
        stats["label_%d" % sample.label] += 1
        flagged = {s.line for s in analysis.sites if s.verdict == VERDICT_LEAK}
        warned = {s.line for s in analysis.sites if s.verdict == VERDICT_EXCEPTION_LEAK}
        unknown = {s.line for s in analysis.sites if s.verdict == VERDICT_UNKNOWN}
        for site in analysis.sites:
            stats["verdict_" + site.verdict] += 1

        if sample.label == 0:
            if flagged:
                errors.append(
                    "FALSE POSITIVE     %s lines=%s" % (sample.path, sorted(flagged))
                )
            stats["warn_exception_tier"] += len(warned)
            unexpected = unknown - set(sample.expected_unknown_lines)
            if unexpected:
                errors.append(
                    "UNEXPECTED UNKNOWN %s lines=%s" % (sample.path, sorted(unexpected))
                )
        else:
            expected = set(sample.expected_leak_lines)
            if not expected:
                errors.append("LABEL 1 WITHOUT LEAK LINE  %s" % sample.path)
                continue
            missed = expected - flagged
            if missed:
                # A miss that lands on the warning tier is softer; count it apart.
                soft = missed & warned
                # A real leak the rules cannot *prove* is an honest UNKNOWN, not
                # a miss: `scoring.py` hands exactly these to the confidence
                # model. Counting them as false negatives would make the corpus
                # reject its own served population.
                deferred = (missed - soft) & unknown & set(sample.expected_unknown_lines)
                hard = missed - warned - deferred
                if hard:
                    errors.append(
                        "FALSE NEGATIVE     %s lines=%s" % (sample.path, sorted(hard))
                    )
                stats["fn_exception_tier"] += len(soft)
                stats["deferred_to_model"] += len(deferred)

        missing_unknown = set(sample.expected_unknown_lines) - unknown
        if missing_unknown:
            errors.append(
                "MISSING UNKNOWN    %s lines=%s" % (sample.path, sorted(missing_unknown))
            )

    return errors, dict(sorted(stats.items()))


def orphan_files(samples: List[Sample]) -> List[str]:
    """Corpus files on disk that no manifest claims."""
    claimed = {s.path for s in samples}
    orphans = []
    for folder in ("real_code", "mutated_code"):
        root = os.path.join(DATASET, folder)
        if not os.path.isdir(root):
            continue
        for path in iter_python_files(root):
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if rel not in claimed:
                orphans.append(rel)
    return sorted(orphans)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the LeakGuard corpus.")
    parser.add_argument("--no-sha", action="store_true", help="skip sha1 drift checks")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    samples = load_all()
    if not samples:
        print("no manifests found under %s" % DATASET, file=sys.stderr)
        return 1

    errors, stats = verify(samples, strict_sha=not args.no_sha)
    orphans = orphan_files(samples)

    if args.json:
        print(json.dumps({"errors": errors, "stats": stats, "orphans": orphans}, indent=2))
    else:
        print("samples           : %d" % len(samples))
        for key, value in stats.items():
            print("%-18s: %s" % (key, value))
        if orphans:
            print("\nunclaimed files   : %d" % len(orphans))
            for path in orphans[:10]:
                print("  %s" % path)
        if errors:
            print("\nPROBLEMS (%d)" % len(errors))
            for error in errors[:60]:
                print("  %s" % error)
            if len(errors) > 60:
                print("  ... %d more" % (len(errors) - 60))
        else:
            print("\nno problems found")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
