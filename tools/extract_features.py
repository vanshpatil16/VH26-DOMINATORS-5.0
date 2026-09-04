"""Turn the corpus into model-ready feature rows.

One row per **open-site**, not per file: a file with three acquisitions where a
mutation broke one of them contributes one positive and two negatives, and that
distinction is the whole point of a line-accurate label.

Site-level labelling rule
-------------------------
* label-0 sample  -> every site is 0.
* label-1 sample  -> a site is 1 iff its acquisition line is listed in the
  manifest's `expected_leak_lines`; every other site in the same file is 0.

Splitting
---------
Deterministic and **grouped by `family`**, hashed with sha1 so it is stable
across machines and Python versions (`hash()` is salted; it must never be used
here). A family lands entirely in one split. Mutants must inherit the family of
the sample they were derived from — otherwise a mutant and its original straddle
the boundary and the reported F1 roughly doubles.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakguard.detector import analyse_file  # noqa: E402
from leakguard.features import FEATURE_NAMES, extract  # noqa: E402
from tools.corpus_lib import DATASET, ROOT, Sample, ensure_dir  # noqa: E402
from tools.verify_dataset import load_all  # noqa: E402

FEATURES_DIR = os.path.join(DATASET, "features")
SPLITS_DIR = os.path.join(DATASET, "splits")
REPORTS_DIR = os.path.join(DATASET, "reports")

#: Percent of families in each split. Grouped, so realised row counts drift from
#: these a little — that is expected, and honest.
SPLIT_BOUNDS = (("train", 70), ("val", 85), ("test", 100))

METADATA_COLUMNS = (
    "row_id", "sample_id", "path", "folder", "origin", "family", "split",
    "sample_label", "label", "operator", "edge_cases", "line", "handle",
    "resource_call", "resource_type", "scope", "class_name", "verdict",
    "exposure",
)


def split_for(family: str) -> str:
    """Stable, salt-free group assignment."""
    digest = hashlib.sha1(family.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    for name, upper in SPLIT_BOUNDS:
        if bucket < upper:
            return name
    return "test"


def rows_for(sample: Sample) -> List[Dict[str, object]]:
    abs_path = os.path.join(ROOT, sample.path.replace("/", os.sep))
    analysis = analyse_file(abs_path)
    if analysis.parse_error:
        return []
    leak_lines = set(sample.expected_leak_lines)
    split = split_for(sample.family)
    rows: List[Dict[str, object]] = []
    for site in analysis.sites:
        vector = extract(site)
        label = 1 if (sample.label == 1 and site.line in leak_lines) else 0
        row: Dict[str, object] = {
            "row_id": "%s#%d:%s" % (sample.sample_id, site.line, site.handle),
            "sample_id": sample.sample_id,
            "path": sample.path,
            "folder": sample.folder,
            "origin": sample.origin,
            "family": sample.family,
            "split": split,
            "sample_label": sample.label,
            "label": label,
            "operator": sample.operator or "",
            "edge_cases": "|".join(sample.edge_cases),
            "line": site.line,
            "handle": site.handle,
            "resource_call": site.call,
            "resource_type": site.resource_type,
            "scope": site.scope,
            "class_name": site.class_name or "",
            "verdict": site.verdict,
            "exposure": vector.exposure,
        }
        row.update({name: vector.values[name] for name in FEATURE_NAMES})
        rows.append(row)
    return rows


def write_jsonl(path: str, rows: List[Dict[str, object]]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    ensure_dir(os.path.dirname(path))
    columns = list(METADATA_COLUMNS) + list(FEATURE_NAMES)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarise(rows: List[Dict[str, object]]) -> Dict[str, object]:
    by_split: collections.Counter = collections.Counter()
    by_split_label: collections.Counter = collections.Counter()
    by_verdict: collections.Counter = collections.Counter()
    by_type: collections.Counter = collections.Counter()
    by_operator: collections.Counter = collections.Counter()
    families: Dict[str, set] = collections.defaultdict(set)
    for row in rows:
        split = str(row["split"])
        by_split[split] += 1
        by_split_label["%s/label_%s" % (split, row["label"])] += 1
        by_verdict[str(row["verdict"])] += 1
        by_type[str(row["resource_type"])] += 1
        if row["operator"]:
            by_operator[str(row["operator"])] += 1
        families[split].add(str(row["family"]))
    positives = sum(1 for row in rows if row["label"] == 1)
    return {
        "rows": len(rows),
        "positives": positives,
        "negatives": len(rows) - positives,
        "positive_rate": round(positives / len(rows), 4) if rows else 0.0,
        "rows_by_split": dict(sorted(by_split.items())),
        "rows_by_split_label": dict(sorted(by_split_label.items())),
        "families_by_split": {k: len(v) for k, v in sorted(families.items())},
        "rules_verdicts": dict(sorted(by_verdict.items())),
        "resource_types": dict(sorted(by_type.items())),
        "mutation_operators": dict(sorted(by_operator.items())),
        "feature_names": list(FEATURE_NAMES),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract LeakGuard feature rows.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    samples = load_all()
    rows: List[Dict[str, object]] = []
    for sample in samples:
        rows.extend(rows_for(sample))
    rows.sort(key=lambda r: str(r["row_id"]))

    write_jsonl(os.path.join(FEATURES_DIR, "features.jsonl"), rows)
    write_csv(os.path.join(FEATURES_DIR, "features.csv"), rows)

    for split, _bound in SPLIT_BOUNDS:
        subset = [row for row in rows if row["split"] == split]
        write_jsonl(os.path.join(SPLITS_DIR, "%s.jsonl" % split), subset)

    spec = {
        "feature_names": list(FEATURE_NAMES),
        "metadata_columns": list(METADATA_COLUMNS),
        "label": "1 = this acquisition leaks, 0 = it is released or unprovable",
        "split_rule": "sha1(family) mod 100, bucketed at %s" % (SPLIT_BOUNDS,),
        "site_label_rule": (
            "a site is positive only when its acquisition line appears in the "
            "sample manifest expected_leak_lines"
        ),
    }
    ensure_dir(FEATURES_DIR)
    with open(os.path.join(FEATURES_DIR, "feature_spec.json"), "w",
              encoding="utf-8", newline="\n") as handle:
        json.dump(spec, handle, indent=2, sort_keys=True)
        handle.write("\n")

    stats = summarise(rows)
    ensure_dir(REPORTS_DIR)
    with open(os.path.join(REPORTS_DIR, "dataset_stats.json"), "w",
              encoding="utf-8", newline="\n") as handle:
        json.dump(stats, handle, indent=2, sort_keys=True)
        handle.write("\n")

    if not args.quiet:
        print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
