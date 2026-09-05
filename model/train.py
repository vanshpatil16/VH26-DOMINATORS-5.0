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

from leakguard.features import (  # noqa: E402
    EXPOSURE_ASYNC,
    EXPOSURE_IN_LOOP,
    EXPOSURE_ROUTE,
    FEATURE_NAMES,
)
from model.pipeline import (  # noqa: E402
    ARTIFACTS_DIR,
    MODEL_VERSION,
    Split,
    breakdown,
    brier,
    confusion,
    conformal_threshold,
    cross_fit_scores,
    expected_calibration_error,
    fit_logistic,
    fit_platt,
    load_all,
    log_loss,
    prf,
    reliability,
    rules_only_baseline,
    select_l2,
)

#: Mirrors the `leakguard.max_false_alarm_rate` config key from the spec.
DEFAULT_MAX_FALSE_ALARM = 0.05

#: Ridge strengths searched by grouped cross-validation. The previous default
#: was the literal 1.0, unjustified; now the corpus picks from this grid and the
#: whole search is recorded in the artifact.
DEFAULT_L2_GRID = (0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)

#: Folds for the grouped cross-fit. Families never straddle a fold.
DEFAULT_FOLDS = 5

#: The one verdict `leakguard/scoring.py` actually asks the model about.
#: DEFINITE_LEAK, EXCEPTION_PATH_LEAK and SAFE are terminal: a probability never
#: overrules a proof. Fitting on those rows taught the model to be a lossy copy
#: of the rules and measured nothing about the job it is deployed to do.
SERVED_VERDICT = "UNKNOWN"

#: Blocking gate on `risk = P(leak) x exposure`, in units of exposure. Unlike the
#: probability threshold this is *not* derived from the corpus: it is a stated
#: policy anchor meaning "one full unit of blast radius". A baseline resource
#: (weight 1.0, no loop/route/async amplification) can therefore never be
#: promoted to LIKELY_LEAK on confidence alone -- it caps at POSSIBLE_LEAK.
#: It lives here, and is written into model.json, so the whole decision boundary
#: is one reviewable artifact rather than a literal buried in the scorer.
DEFAULT_RISK_THRESHOLD = 1.0


def _scoped(split: Split, scope: str) -> Split:
    """Restrict a split to the rows the model is consulted for.

    `scope="all"` keeps every site and reproduces the old behaviour, which is
    kept because it is the ablation that shows why the change was needed.
    """
    if scope == "all":
        return split
    rows = [row for row in split.rows if row.get("verdict") == SERVED_VERDICT]
    return Split(name=split.name, rows=rows)


def _families(split: Split) -> List[str]:
    return [str(row["family"]) for row in split.rows]


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
    parser.add_argument("--l2", type=float, default=None,
                        help="ridge strength on the weights (never the bias); "
                             "omit to select it by grouped cross-validation")
    parser.add_argument("--scope", choices=("served", "all"), default="served",
                        help="'served' fits only the rules-UNKNOWN sites the "
                             "scorer consults the model about; 'all' fits every "
                             "site, which is the pre-change ablation")
    parser.add_argument("--folds", type=int, default=DEFAULT_FOLDS,
                        help="grouped cross-fit folds for calibration")
    parser.add_argument("--max-false-alarm", type=float, default=DEFAULT_MAX_FALSE_ALARM,
                        help="conformal tolerance the gate threshold is derived from")
    parser.add_argument("--risk-threshold", type=float, default=DEFAULT_RISK_THRESHOLD,
                        help="exposure-weighted risk at which a site blocks CI")
    parser.add_argument("--artifacts", default=ARTIFACTS_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    splits = load_all()
    raw_train, raw_val, raw_test = splits["train"], splits["val"], splits["test"]
    train = _scoped(raw_train, args.scope)
    val = _scoped(raw_val, args.scope)
    test = _scoped(raw_test, args.scope)

    if not len(train):
        print("no training rows in scope %r. Run: python tools/extract_features.py"
              % args.scope, file=sys.stderr)
        return 1

    if train.positives == 0:
        print(
            "The corpus has %d training rows in scope %r but 0 positives.\n"
            "Training a classifier on one class would produce a model that has\n"
            "never seen a leak, so nothing was written.\n\n"
            "For the served scope, generate ownership escapes with known ground\n"
            "truth, then rerun:\n"
            "  python tools/synthesize_escapes.py\n"
            "  python tools/extract_features.py && python model/train.py"
            % (len(train), args.scope),
            file=sys.stderr,
        )
        return 0

    # Development set = train + val. The weights, the calibration and the gate
    # are all derived from it by grouped cross-fitting; test is never touched
    # until the final evaluation.
    development = Split(name="development", rows=train.rows + val.rows)
    groups = _families(development)
    folds = max(2, min(args.folds, len(set(groups))))

    if args.l2 is None:
        l2, l2_trace = select_l2(development.X, development.y, groups,
                                 DEFAULT_L2_GRID, folds)
    else:
        l2, l2_trace = args.l2, []

    # Out-of-fold scores: every development row scored by a model that never saw
    # its family. This is what Platt and the conformal quantile are fitted on.
    oof_scores = cross_fit_scores(development.X, development.y, groups, l2, folds)
    scaler = fit_platt(oof_scores, development.y)
    oof_probabilities = [scaler(score) for score in oof_scores]

    negative_scores = [
        probability
        for probability, label in zip(oof_probabilities, development.y)
        if label == 0
    ]
    threshold = conformal_threshold(negative_scores, args.max_false_alarm)

    # Final weights: refit on the whole development set at the chosen strength.
    model = fit_logistic(development.X, development.y, l2=l2)

    test_probabilities = _probabilities(model, scaler, test)
    metrics = {
        "threshold": round(threshold, 6),
        "max_false_alarm_rate": args.max_false_alarm,
        "scope": args.scope,
        "calibration_split": "development (grouped %d-fold cross-fit)" % folds,
        "l2": l2,
        "l2_search": l2_trace,
        "cross_fit": {
            "folds": folds,
            "families": len(set(groups)),
            "rows": len(development),
            "positives": development.positives,
            "log_loss": log_loss(oof_probabilities, development.y),
            "brier": brier(oof_probabilities, development.y),
            "calibration_negatives": len(negative_scores),
        },
        "out_of_fold": _evaluate(development, oof_probabilities, threshold),
        "train": _evaluate(train, _probabilities(model, scaler, train), threshold),
        "val": _evaluate(val, _probabilities(model, scaler, val), threshold),
        "test": _evaluate(test, test_probabilities, threshold),
    }
    if args.scope != "all":
        # What the model would say if it were asked about every site, including
        # the ones the rules already decide. Reported so the train/serve gap is
        # visible rather than implied.
        every = _scoped(raw_test, "all")
        metrics["test_all_sites_reference"] = _evaluate(
            every, _probabilities(model, scaler, every), threshold)

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
        # The second gate. Derived from policy, not from the corpus -- and said
        # so here, because a reviewer is entitled to know which of the two
        # numbers the data chose and which one a human did.
        "risk_threshold": {
            "value": args.risk_threshold,
            "derivation": "policy anchor: one unit of exposure, not fitted",
            "applies_to": "promotion of a rules-UNKNOWN site to LIKELY_LEAK",
        },
        # Recorded for provenance only. `leakguard/features.py` stays the source
        # of truth: exposure is computed during feature extraction, which builds
        # the corpus this model is fitted on, so reading the multipliers back out
        # of this artifact at extraction time would be circular.
        "exposure_multipliers": {
            "in_loop": EXPOSURE_IN_LOOP,
            "route": EXPOSURE_ROUTE,
            "is_async": EXPOSURE_ASYNC,
            "source_of_truth": "leakguard/features.py",
            "formula": "exposure = resource_weight * in_loop? * route? * is_async?",
        },
        # The bucketing contract, spelled out next to the numbers that implement
        # it. Rules-proven verdicts are terminal: a probability never overrules a
        # proof, it only adjudicates what the analyser could not decide.
        "verdict_tiers": {
            "DEFINITE_LEAK": "analyser proved an unclosed exit path; model not consulted",
            "LIKELY_LEAK": "rules UNKNOWN, p_leak >= threshold, risk >= risk_threshold",
            "POSSIBLE_LEAK": "analyser proved closure on normal paths only, OR "
                             "rules UNKNOWN with p_leak >= threshold but risk < risk_threshold",
            "SAFE": "analyser proved closure on every path, OR p_leak < threshold",
            "blocking": ["DEFINITE_LEAK", "LIKELY_LEAK"],
            "advisory": ["POSSIBLE_LEAK"],
        },
        "training": {
            "l2": l2,
            "l2_selection": ("grouped %d-fold CV over %s" % (folds, list(DEFAULT_L2_GRID))
                             if args.l2 is None else "fixed by --l2"),
            "scope": args.scope,
            "scope_meaning": (
                "rows whose rules verdict is UNKNOWN -- the only verdict "
                "leakguard/scoring.py consults the model about"
                if args.scope != "all" else "every acquisition site"),
            "train_rows": len(train),
            "train_positives": train.positives,
            "val_rows": len(val),
            "val_positives": val.positives,
            "development_rows": len(development),
            "development_positives": development.positives,
            "calibration": "Platt on grouped %d-fold out-of-fold scores" % folds,
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
                "scope": args.scope,
                "l2": l2,
                "cross_fit": metrics["cross_fit"],
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
