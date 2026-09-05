"""Training pipeline internals: data loading, logistic regression, calibration.

Pure standard library on purpose. The model is ~15 numbers; pulling in numpy and
scikit-learn to fit it would put a dependency wall between the analyser and CI
for no benefit, and would make the "same commit SHA, same verdict" guarantee
depend on a BLAS version.

Nothing here runs at scan time. Scanning loads `model/artifacts/model.json` and
evaluates one dot product. Recalibration is an explicit offline command that
emits a reviewable diff.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from leakguard.features import FEATURE_NAMES  # noqa: E402

DATASET = os.path.join(ROOT, "dataset")
SPLITS_DIR = os.path.join(DATASET, "splits")
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

MODEL_VERSION = 1


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


@dataclass
class Split:
    name: str
    rows: List[dict] = field(default_factory=list)

    @property
    def X(self) -> List[List[float]]:
        return [[float(row[name]) for name in FEATURE_NAMES] for row in self.rows]

    @property
    def y(self) -> List[int]:
        return [int(row["label"]) for row in self.rows]

    @property
    def positives(self) -> int:
        return sum(self.y)

    def __len__(self) -> int:
        return len(self.rows)


def load_split(name: str, splits_dir: str = SPLITS_DIR) -> Split:
    path = os.path.join(splits_dir, "%s.jsonl" % name)
    rows: List[dict] = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return Split(name=name, rows=rows)


def load_all(splits_dir: str = SPLITS_DIR) -> Dict[str, Split]:
    return {name: load_split(name, splits_dir) for name in ("train", "val", "test")}


# --------------------------------------------------------------------------- #
# Linear algebra (14 features: a dense solve is nothing)
# --------------------------------------------------------------------------- #


def solve(matrix: List[List[float]], rhs: List[float]) -> Optional[List[float]]:
    """Gaussian elimination with partial pivoting. None when singular."""
    size = len(rhs)
    augmented = [list(matrix[i]) + [rhs[i]] for i in range(size)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            return None
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        for row in range(col + 1, size):
            factor = augmented[row][col] / pivot_value
            if factor == 0.0:
                continue
            for k in range(col, size + 1):
                augmented[row][k] -= factor * augmented[col][k]
    out = [0.0] * size
    for row in range(size - 1, -1, -1):
        total = augmented[row][size]
        for col in range(row + 1, size):
            total -= augmented[row][col] * out[col]
        out[row] = total / augmented[row][row]
    return out


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


# --------------------------------------------------------------------------- #
# Logistic regression (IRLS with ridge)
# --------------------------------------------------------------------------- #


@dataclass
class LogisticModel:
    weights: List[float]
    bias: float

    def score(self, features: Sequence[float]) -> float:
        """Raw log-odds, before Platt scaling."""
        return self.bias + sum(w * x for w, x in zip(self.weights, features))

    def predict(self, features: Sequence[float]) -> float:
        return sigmoid(self.score(features))


def fit_logistic(
    X: List[List[float]],
    y: List[int],
    l2: float = 1.0,
    iterations: int = 50,
    balance: bool = True,
    tolerance: float = 1e-8,
) -> LogisticModel:
    """Iteratively reweighted least squares.

    Deterministic: no shuffling, no random init, fixed iteration cap with an
    early stop on parameter change. Class weights default to balanced, because a
    corpus that is 90% negative otherwise trains a model that predicts "safe"
    and scores well doing it.
    """
    if not X:
        raise ValueError("cannot fit on an empty split")
    n_features = len(X[0])
    size = n_features + 1
    beta = [0.0] * size

    positives = sum(y)
    negatives = len(y) - positives
    if balance and positives and negatives:
        weight_pos = len(y) / (2.0 * positives)
        weight_neg = len(y) / (2.0 * negatives)
    else:
        weight_pos = weight_neg = 1.0
    sample_weight = [weight_pos if label else weight_neg for label in y]

    design = [[1.0] + list(row) for row in X]

    for _ in range(iterations):
        hessian = [[0.0] * size for _ in range(size)]
        gradient = [0.0] * size
        for row, label, weight in zip(design, y, sample_weight):
            eta = sum(b * v for b, v in zip(beta, row))
            mu = sigmoid(eta)
            variance = max(mu * (1.0 - mu), 1e-9) * weight
            residual = (label - mu) * weight
            for i in range(size):
                gradient[i] += residual * row[i]
                row_i = row[i] * variance
                for j in range(i, size):
                    hessian[i][j] += row_i * row[j]
        for i in range(size):
            for j in range(i):
                hessian[i][j] = hessian[j][i]
        # Ridge on the weights, never on the bias: penalising the intercept
        # shifts the base rate and wrecks calibration.
        for i in range(1, size):
            hessian[i][i] += l2
            gradient[i] -= l2 * beta[i]

        step = solve(hessian, gradient)
        if step is None:
            break
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < tolerance:
            break

    return LogisticModel(weights=beta[1:], bias=beta[0])


# --------------------------------------------------------------------------- #
# Platt scaling
# --------------------------------------------------------------------------- #


@dataclass
class PlattScaler:
    a: float = 1.0
    b: float = 0.0

    def __call__(self, raw_score: float) -> float:
        return sigmoid(self.a * raw_score + self.b)

    def as_dict(self) -> Dict[str, float]:
        return {"a": round(self.a, 8), "b": round(self.b, 8)}


def fit_platt(scores: Sequence[float], labels: Sequence[int],
              iterations: int = 100) -> PlattScaler:
    """One-dimensional logistic fit on held-out raw scores.

    Uses the Platt/Lin smoothing targets so a perfectly separable validation set
    does not drive the parameters to infinity.
    """
    if not scores:
        return PlattScaler()
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return PlattScaler()
    hi = 1.0 / (positives + 2.0)
    lo = 1.0 / (negatives + 2.0)
    targets = [1.0 - hi if label else lo for label in labels]

    a, b = 1.0, 0.0
    for _ in range(iterations):
        h11 = h22 = h12 = g1 = g2 = 0.0
        for score, target in zip(scores, targets):
            eta = a * score + b
            mu = sigmoid(eta)
            variance = max(mu * (1.0 - mu), 1e-9)
            residual = target - mu
            g1 += residual * score
            g2 += residual
            h11 += variance * score * score
            h12 += variance * score
            h22 += variance
        h11 += 1e-9
        h22 += 1e-9
        det = h11 * h22 - h12 * h12
        if abs(det) < 1e-12:
            break
        da = (h22 * g1 - h12 * g2) / det
        db = (h11 * g2 - h12 * g1) / det
        a += da
        b += db
        if max(abs(da), abs(db)) < 1e-10:
            break
    return PlattScaler(a=a, b=b)


# --------------------------------------------------------------------------- #
# Split-conformal threshold
# --------------------------------------------------------------------------- #


def conformal_threshold(negative_scores: Sequence[float], max_false_alarm: float) -> float:
    """Smallest threshold whose false-alarm rate is bounded by the tolerance.

    Split conformal on the negatives of the calibration split. With `n`
    calibration negatives, taking the `ceil((n + 1) * (1 - alpha))`-th smallest
    score gives a finite-sample guarantee that a fresh negative exceeds it with
    probability at most `alpha`. The threshold therefore falls out of a stated
    tolerance instead of being hand-picked — the direct answer to "teams disable
    noisy analyzers".
    """
    if not negative_scores:
        return 0.5
    ordered = sorted(negative_scores)
    n = len(ordered)
    rank = math.ceil((n + 1) * (1.0 - max_false_alarm))
    if rank >= n:
        # Not enough calibration data to certify the tolerance: refuse to flag
        # on confidence alone rather than guess.
        return 1.0
    return float(ordered[max(rank - 1, 0)])


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def confusion(probabilities: Sequence[float], labels: Sequence[int],
              threshold: float) -> Dict[str, int]:
    tp = fp = tn = fn = 0
    for probability, label in zip(probabilities, labels):
        flagged = probability >= threshold
        if label == 1 and flagged:
            tp += 1
        elif label == 1:
            fn += 1
        elif flagged:
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def prf(counts: Dict[str, int]) -> Dict[str, float]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    negatives = counts["fp"] + counts["tn"]
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_alarm_rate": round(fp / negatives, 4) if negatives else 0.0,
    }


def brier(probabilities: Sequence[float], labels: Sequence[int]) -> float:
    if not probabilities:
        return 0.0
    total = sum((p - y) ** 2 for p, y in zip(probabilities, labels))
    return round(total / len(probabilities), 6)


def reliability(probabilities: Sequence[float], labels: Sequence[int],
                bins: int = 10) -> List[Dict[str, float]]:
    """Reliability-diagram rows: predicted vs observed frequency per bin."""
    buckets: List[List[Tuple[float, int]]] = [[] for _ in range(bins)]
    for probability, label in zip(probabilities, labels):
        index = min(int(probability * bins), bins - 1)
        buckets[index].append((probability, label))
    rows = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            rows.append({
                "bin_lower": round(index / bins, 3),
                "bin_upper": round((index + 1) / bins, 3),
                "count": 0,
                "mean_predicted": 0.0,
                "observed_rate": 0.0,
            })
            continue
        mean_predicted = sum(p for p, _ in bucket) / len(bucket)
        observed = sum(y for _, y in bucket) / len(bucket)
        rows.append({
            "bin_lower": round(index / bins, 3),
            "bin_upper": round((index + 1) / bins, 3),
            "count": len(bucket),
            "mean_predicted": round(mean_predicted, 4),
            "observed_rate": round(observed, 4),
        })
    return rows


def expected_calibration_error(rows: Sequence[Dict[str, float]], total: int) -> float:
    if not total:
        return 0.0
    error = sum(
        row["count"] / total * abs(row["mean_predicted"] - row["observed_rate"])
        for row in rows
    )
    return round(error, 6)


def rules_only_baseline(rows: Sequence[dict]) -> Dict[str, object]:
    """How the deterministic verdicts alone score — the ablation that matters.

    If the model cannot beat this, ship the rules and say so in the write-up.
    """
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for row in rows:
        flagged = row["verdict"] == "DEFINITE_LEAK"
        label = int(row["label"])
        if label == 1 and flagged:
            counts["tp"] += 1
        elif label == 1:
            counts["fn"] += 1
        elif flagged:
            counts["fp"] += 1
        else:
            counts["tn"] += 1
    return {"counts": counts, **prf(counts)}


def breakdown(rows: Sequence[dict], probabilities: Sequence[float],
              threshold: float, key: str) -> Dict[str, Dict[str, object]]:
    """Per-operator / per-edge-case recall, so a blind spot is visible."""
    groups: Dict[str, List[int]] = {}
    hits: Dict[str, int] = {}
    for row, probability in zip(rows, probabilities):
        if int(row["label"]) != 1:
            continue
        raw = str(row.get(key) or "")
        names = raw.split("|") if key == "edge_cases" else [raw]
        for name in names:
            if not name:
                continue
            groups.setdefault(name, []).append(1)
            if probability >= threshold:
                hits[name] = hits.get(name, 0) + 1
    return {
        name: {
            "positives": len(values),
            "detected": hits.get(name, 0),
            "recall": round(hits.get(name, 0) / len(values), 4),
        }
        for name, values in sorted(groups.items())
    }


# --------------------------------------------------------------------------- #
# Grouped cross-fitting
# --------------------------------------------------------------------------- #


def group_folds(groups: Sequence[str], k: int = 5) -> List[List[int]]:
    """Deterministic grouped K-fold: a family is never split across folds.

    Families are dealt largest-first into whichever fold is currently smallest,
    with sha1 breaking ties. No RNG, no `hash()` (it is salted per process), so
    the folds are identical on every machine and the fitted artifact stays
    byte-reproducible.
    """
    sizes: Dict[str, int] = {}
    for group in groups:
        sizes[group] = sizes.get(group, 0) + 1
    ordered = sorted(
        sizes,
        key=lambda g: (-sizes[g], hashlib.sha1(g.encode("utf-8")).hexdigest()),
    )
    fold_of: Dict[str, int] = {}
    loads = [0] * k
    for group in ordered:
        index = min(range(k), key=lambda i: (loads[i], i))
        fold_of[group] = index
        loads[index] += sizes[group]
    folds: List[List[int]] = [[] for _ in range(k)]
    for index, group in enumerate(groups):
        folds[fold_of[group]].append(index)
    return folds


def cross_fit_scores(
    X: List[List[float]],
    y: List[int],
    groups: Sequence[str],
    l2: float,
    k: int = 5,
) -> List[float]:
    """Out-of-fold raw log-odds for every row.

    Calibrating on a single held-out split is what produced the 86% test
    false-alarm rate: with grouped splits that split held 8 families and none of
    the hard negative class. Cross-fitting gives a calibration score for *every*
    development row, from a model that never saw that row's family, so Platt
    scaling and the conformal quantile both get the whole corpus to work with.
    """
    scores = [0.0] * len(y)
    for fold in group_folds(groups, k):
        held = set(fold)
        keep = [i for i in range(len(y)) if i not in held]
        if not keep or not any(y[i] for i in keep):
            continue
        model = fit_logistic([X[i] for i in keep], [y[i] for i in keep], l2=l2)
        for i in fold:
            scores[i] = model.score(X[i])
    return scores


def log_loss(probabilities: Sequence[float], labels: Sequence[int]) -> float:
    if not probabilities:
        return 0.0
    total = 0.0
    for probability, label in zip(probabilities, labels):
        clipped = min(max(probability, 1e-12), 1.0 - 1e-12)
        total -= math.log(clipped) if label else math.log(1.0 - clipped)
    return round(total / len(probabilities), 6)


def select_l2(
    X: List[List[float]],
    y: List[int],
    groups: Sequence[str],
    grid: Sequence[float],
    k: int = 5,
) -> Tuple[float, List[Dict[str, float]]]:
    """Pick the ridge strength by grouped cross-validated log loss.

    The old value was the literal 1.0 with no justification. Ties go to the
    stronger penalty, which is the 1-SE spirit: prefer the simpler boundary when
    the data cannot tell two apart.
    """
    trace: List[Dict[str, float]] = []
    best: Optional[Tuple[float, float]] = None
    for l2 in grid:
        raw = cross_fit_scores(X, y, groups, l2, k)
        scaler = fit_platt(raw, y)
        loss = log_loss([scaler(score) for score in raw], y)
        trace.append({"l2": l2, "cv_log_loss": loss})
        if best is None or loss < best[1] - 1e-9 or (
            abs(loss - best[1]) <= 1e-9 and l2 > best[0]
        ):
            best = (l2, loss)
    return (best[0] if best else 1.0), trace
