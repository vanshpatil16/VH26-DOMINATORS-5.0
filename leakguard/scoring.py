"""Explainable AI (XAI) confidence scoring and feature attribution for LeakGuard.

Evaluates the offline calibrated logistic model against extracted feature vectors,
producing:
1. Calibrated leak probability P(leak) via Platt scaling.
2. Exposure-weighted Risk score: Risk = P(leak) x exposure.
3. Feature Attributions: Exact log-odds breakdown (w_i * x_i) explaining why
   the model flagged or cleared the site.
4. Counterfactual "What-If" Analysis: Computes how the risk would change if the
   code were refactored (e.g. wrapped in `with` or guarded by `finally`).
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .detector import (
    VERDICT_EXCEPTION_LEAK,
    VERDICT_LEAK,
    VERDICT_SAFE,
    VERDICT_UNKNOWN,
    OpenSite,
    analyse_module,
)
from .features import FEATURE_NAMES, FeatureVector, describe, extract

MODEL_ARTIFACT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model",
    "artifacts",
    "model.json",
)

# Human-readable templates for feature contributions
FEATURE_DESCRIPTIONS = {
    "leaking_path_fraction": "Fraction of CFG exit paths where resource is unclosed",
    "raising_call_between": "Potentially raising call sits between acquire and release",
    "in_loop": "Acquired inside a loop body (descriptor exhaustion risk)",
    "close_present_but_unguarded": "Close statement exists but is unguarded against exceptions",
    "reassigned_before_close": "Variable rebound before previous handle was closed",
    "resource_type_weight": "Registry blast-radius weight for resource type",
    "escapes_self_attr": "Handle stored on object instance attribute (intra-class ownership)",
    "escapes_return": "Handle returned to caller (ownership transfer)",
    "escapes_container": "Handle appended to collection/container",
    "escapes_call_arg": "Handle passed as argument to unresolved function call",
    "is_async_resource": "Resource requires async cleanup (aexit/close)",
    "is_test_or_script_file": "File is test fixture or top-level script",
    "callee_closes_param": "Callee function summary confirms parameter release",
    "callee_name_suggests_close": "Passed to a function whose name indicates cleanup",
    "escape_disposed_downstream": "A caller in this module demonstrably releases the escaped handle",
    "escape_recipient_unknown": "Nothing in this module consumes the escaped handle",
    "container_drained_in_module": "The container the handle enters is drained by a close loop",
}


@dataclass(frozen=True)
class FeatureAttribution:
    feature_name: str
    value: float
    weight: float
    contribution: float          # weight * value (log-odds impact)
    description: str             # Human explanation
    is_risk_increasing: bool     # True if pushes towards LEAK


@dataclass
class ScoredSite:
    site: OpenSite
    vector: FeatureVector
    filename: str
    p_leak: float
    exposure: float
    risk: float
    threshold: float
    rule_verdict: str
    final_verdict: str           # DEFINITE_LEAK | LIKELY_LEAK | POSSIBLE_LEAK | SAFE
    attributions: List[FeatureAttribution] = field(default_factory=list)
    evidence_lines: List[str] = field(default_factory=list)
    counterfactual_p_leak: float = 0.0
    counterfactual_risk: float = 0.0
    fix_suggestion: str = ""

    @property
    def is_blocking(self) -> bool:
        """Determines whether this finding fails a CI build."""
        return self.final_verdict in ("DEFINITE_LEAK", "LIKELY_LEAK")


class ConfidenceModel:
    """Zero-dependency inference engine for the serialized logistic model."""

    def __init__(self, artifact_path: str = MODEL_ARTIFACT_PATH):
        self.artifact_path = artifact_path
        self.weights: Dict[str, float] = {}
        self.bias: float = -3.5
        self.platt_a: float = 1.0
        self.platt_b: float = 0.0
        self.threshold: float = 0.07
        self.risk_threshold: float = 1.0
        self.loaded: bool = False
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.artifact_path):
            try:
                with open(self.artifact_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self.weights = {k: float(v) for k, v in data.get("weights", {}).items()}
                self.bias = float(data.get("bias", -3.5))
                platt = data.get("platt", {})
                self.platt_a = float(platt.get("a", 1.0))
                self.platt_b = float(platt.get("b", 0.0))
                thresh = data.get("threshold", {})
                self.threshold = float(thresh.get("value", 0.07))
                # Second gate: exposure-weighted risk at which a site blocks CI.
                # Written by model/train.py so the full decision boundary lives
                # in the artifact rather than as a literal in this file.
                risk_gate = data.get("risk_threshold", {})
                self.risk_threshold = float(risk_gate.get("value", 1.0))
                self.loaded = True
            except Exception:
                self._set_default_weights()
        else:
            self._set_default_weights()

    def _set_default_weights(self) -> None:
        self.weights = {
            "leaking_path_fraction": 7.5,
            "raising_call_between": 1.5,
            "in_loop": 1.2,
            "close_present_but_unguarded": 0.5,
            "reassigned_before_close": 0.8,
            "resource_type_weight": 0.1,
            "escapes_self_attr": -0.8,
            "escapes_return": -0.2,
            "escapes_container": -0.1,
            "escapes_call_arg": -0.1,
            "is_async_resource": -0.5,
            "is_test_or_script_file": -0.2,
            "callee_closes_param": -1.5,
            "callee_name_suggests_close": -0.8,
        }
        self.bias = -3.5
        self.platt_a = 1.2
        self.platt_b = -0.3
        self.threshold = 0.07
        self.risk_threshold = 1.0
        self.loaded = False

    def predict_p_leak(self, values: Dict[str, float]) -> Tuple[float, List[FeatureAttribution]]:
        logit = self.bias
        attributions: List[FeatureAttribution] = []

        for name in FEATURE_NAMES:
            val = float(values.get(name, 0.0))
            w = float(self.weights.get(name, 0.0))
            contrib = w * val
            logit += contrib
            if abs(contrib) > 0.001 or (val > 0 and abs(w) > 0.01):
                attributions.append(
                    FeatureAttribution(
                        feature_name=name,
                        value=val,
                        weight=round(w, 4),
                        contribution=round(contrib, 4),
                        description=FEATURE_DESCRIPTIONS.get(name, name),
                        is_risk_increasing=(contrib > 0),
                    )
                )

        # Sort attributions by absolute impact magnitude
        attributions.sort(key=lambda a: abs(a.contribution), reverse=True)

        # Apply Platt calibration: sigmoid(a * logit + b)
        scaled_z = self.platt_a * logit + self.platt_b
        # Numerical stability clamp
        scaled_z = max(-30.0, min(30.0, scaled_z))
        p_leak = 1.0 / (1.0 + math.exp(-scaled_z))
        return p_leak, attributions

    def score(self, site: OpenSite, vector: FeatureVector, filename: str = "<unknown>") -> ScoredSite:
        p_leak, attributions = self.predict_p_leak(vector.values)
        exposure = vector.exposure
        risk = round(p_leak * exposure, 4)
        evidence = describe(vector)

        # Counterfactual: what would have to change for this to be safe?
        # For a site the CFG decides, that is "wrap it in a context manager".
        # For an *escape* -- the only kind the model actually adjudicates -- the
        # in-function path features are already clean and flipping them changes
        # nothing, which is why this used to report "0.0% reduction -> SAFE".
        # The lever that applies there is the recipient releasing the handle.
        counterfactual_vals = dict(vector.values)
        counterfactual_vals["leaking_path_fraction"] = 0.0
        counterfactual_vals["close_present_but_unguarded"] = 0.0
        counterfactual_vals["raising_call_between"] = 0.0
        if site.verdict == VERDICT_UNKNOWN:
            counterfactual_vals["escape_disposed_downstream"] = 1.0
            counterfactual_vals["escape_recipient_unknown"] = 0.0
            if vector.values.get("escapes_container"):
                counterfactual_vals["container_drained_in_module"] = 1.0
        cf_p_leak, _ = self.predict_p_leak(counterfactual_vals)
        cf_risk = round(cf_p_leak * exposure, 4)

        # Determine final explainable verdict tier
        if site.verdict == VERDICT_LEAK:
            final_verdict = "DEFINITE_LEAK"
            fix_suggestion = f"Wrap '{site.call}' in a 'with' block or ensure '{site.handle}.close()' executes on all exit paths."
        elif site.verdict == VERDICT_EXCEPTION_LEAK:
            final_verdict = "POSSIBLE_LEAK"
            fix_suggestion = f"Guarding cleanup with 'try...finally' or 'with' protects against unhandled exceptions between lines {site.line} and exit."
        elif site.verdict == VERDICT_SAFE:
            final_verdict = "SAFE"
            fix_suggestion = "Properly managed (all paths closed)."
        else:  # UNKNOWN
            if p_leak >= self.threshold and risk >= self.risk_threshold:
                final_verdict = "LIKELY_LEAK"
                fix_suggestion = (
                    f"High confidence leak ({p_leak:.1%}): ownership leaves "
                    f"'{site.scope}' and nothing in this module releases "
                    f"'{site.handle}'. Have the recipient close it, or keep "
                    f"ownership here with a 'with' block.")
            elif p_leak >= self.threshold:
                final_verdict = "POSSIBLE_LEAK"
                fix_suggestion = f"Potential leak ({p_leak:.1%}): verify that '{site.handle}' is closed across all caller paths."
            else:
                final_verdict = "SAFE"
                fix_suggestion = "Confidence model indicates low risk of leakage."

        return ScoredSite(
            site=site,
            vector=vector,
            filename=filename,
            p_leak=round(p_leak, 4),
            exposure=exposure,
            risk=risk,
            threshold=self.threshold,
            rule_verdict=site.verdict,
            final_verdict=final_verdict,
            attributions=attributions,
            evidence_lines=evidence,
            counterfactual_p_leak=round(cf_p_leak, 4),
            counterfactual_risk=cf_risk,
            fix_suggestion=fix_suggestion,
        )


_GLOBAL_MODEL: Optional[ConfidenceModel] = None


def get_model() -> ConfidenceModel:
    global _GLOBAL_MODEL
    if _GLOBAL_MODEL is None:
        _GLOBAL_MODEL = ConfidenceModel()
    return _GLOBAL_MODEL


def score_site(site: OpenSite, filename: str = "<unknown>") -> ScoredSite:
    vector = extract(site)
    return get_model().score(site, vector, filename=filename)


def score_module(source: str, filename: str) -> List[ScoredSite]:
    analysis = analyse_module(source, filename)
    if analysis.parse_error:
        return []
    return [score_site(site, filename=filename) for site in analysis.sites]
