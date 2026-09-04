"""Fit the confidence model and emit reviewable artifacts.

    python model/train.py

Reads `dataset/splits/*.jsonl`, fits on train, calibrates on val, derives the
gate threshold from a stated false-alarm tolerance, and evaluates on test.

Three properties that are not negotiable:

* **Offline only.** This never runs at scan time. Scanning reads
  `model/artifacts/model.json` and evaluates one dot product.
* **Deterministic.** No RNG, no shuffling, no timestamps in the artifacts, so a
  rerun on the same corpus produces a byte-identical `model.json` and any change
  shows up as a reviewable diff.
* **Honest about an empty positive class.** Until the mutation pass lands there
  are no label-1 rows. Rather than emit a model that has never seen a leak, it
  reports what is missing and exits cleanly.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leakguard.features import FEATURE_NAMES  # noqa: E402
from model.pipeline import (  # noqa: E402
    ARTIFACTS_DIR,
    MODEL_VERSION,
    Split,
    breakdown,
    brier,
    confusion,
    conformal_threshold,
    expected_calibration_error,
    fit_logistic,
    fit_platt,
    load_all,
    prf,
    reliability,
    rules_only_baseline,
)

#: Mirrors the `leakguard.max_false_alarm_rate` config key from the spec.
DEFAULT_MAX_FALSE_ALARM = 0.05
DEFAULT_L2 = 1.0


def _ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def _probabilities(model, scaler, split: Split) -> List[float]:
    return [scaler(model.score(features)) for features in split.X]


def _evaluate(split: Split, probabilities: List[float], threshold: float) -> Dict[str, object]:
    labels = split.y
    counts = confusion(probabilities, labels, threshold)
    bins = reliability(probabilities, labels)
    return {
        "rows": len(split),
        "positives": split.positives,
        "counts": counts,
        **prf(counts),
        "brier": brier(probabilities, labels),
        "expected_calibration_error": expected_calibration_error(bins, len(split)),
        "rules_only_baseline": rules_only_baseline(split.rows),
        "recall_by_operator": breakdown(split.rows, probabilities, threshold, "operator"),
        "recall_by_edge_case": breakdown(split.rows, probabilities, threshold, "edge_cases"),
    }


def _write_json(path: str, payload: object) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_reliability(path: str, rows: List[Dict[str, float]]) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["bin_lower", "bin_upper", "count", "mean_predicted", "observed_rate"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Train the LeakGuard confidence model.")
    parser.add_argument("--l2", type=float, default=DEFAULT_L2,
                        help="ridge strength on the weights (never the bias)")
    parser.add_argument("--max-false-alarm", type=float, default=DEFAULT_MAX_FALSE_ALARM,
                        help="conformal tolerance the gate threshold is derived from")
    parser.add_argument("--artifacts", default=ARTIFACTS_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    splits = load_all()
    train, val, test = splits["train"], splits["val"], splits["test"]

    if not len(train):
        print("no training rows. Run: python tools/extract_features.py", file=sys.stderr)
        return 1

    if train.positives == 0:
        print(
            "The corpus has %d training rows but 0 positives -- the mutated_code\n"
            "half has not landed yet. Training a classifier on one class would\n"
            "produce a model that has never seen a leak, so nothing was written.\n\n"
            "Next: generate mutants into dataset/mutated_code/, then rerun\n"
            "  python tools/extract_features.py && python model/train.py"
            % len(train),
            file=sys.stderr,
        )
        return 0

    model = fit_logistic(train.X, train.y, l2=args.l2)

    # Calibrate on the split the weights never saw.
    calibration = val if val.positives else train
    scaler = fit_platt([model.score(f) for f in calibration.X], calibration.y)

    # Threshold from the stated tolerance, using calibration negatives only.
    calibration_probabilities = _probabilities(model, scaler, calibration)
    negative_scores = [
        probability
        for probability, label in zip(calibration_probabilities, calibration.y)
        if label == 0
    ]
    threshold = conformal_threshold(negative_scores, args.max_false_alarm)

    test_probabilities = _probabilities(model, scaler, test)
    metrics = {
        "threshold": round(threshold, 6),
        "max_false_alarm_rate": args.max_false_alarm,
        "calibration_split": calibration.name,
        "train": _evaluate(train, _probabilities(model, scaler, train), threshold),
        "val": _evaluate(val, _probabilities(model, scaler, val), threshold),
        "test": _evaluate(test, test_probabilities, threshold),
    }

    artifact = {
        "version": MODEL_VERSION,
        "feature_names": list(FEATURE_NAMES),
        "weights": {
            name: round(weight, 8)
            for name, weight in zip(FEATURE_NAMES, model.weights)
        },
        "bias": round(model.bias, 8),
        "platt": scaler.as_dict(),
        "threshold": {
            "value": round(threshold, 8),
            "derivation": "split conformal on calibration negatives",
            "max_false_alarm_rate": args.max_false_alarm,
        },
        "training": {
            "l2": args.l2,
            "train_rows": len(train),
            "train_positives": train.positives,
            "val_rows": len(val),
            "val_positives": val.positives,
            "class_weighting": "balanced",
            "optimizer": "IRLS",
        },
    }

    _write_json(os.path.join(args.artifacts, "model.json"), artifact)
    _write_json(os.path.join(args.artifacts, "metrics.json"), metrics)
    _write_reliability(
        os.path.join(args.artifacts, "reliability.csv"),
        reliability(test_probabilities, test.y),
    )

    if not args.quiet:
        print(json.dumps(
            {
                "threshold": metrics["threshold"],
                "test": {
                    key: metrics["test"][key]
                    for key in ("rows", "positives", "counts", "precision",
                                "recall", "f1", "false_alarm_rate", "brier")
                },
                "rules_only_baseline": metrics["test"]["rules_only_baseline"],
                "top_weights": sorted(
                    artifact["weights"].items(), key=lambda kv: -abs(kv[1])
                )[:6],
            },
            indent=2,
            sort_keys=True,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
