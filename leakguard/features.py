"""The 14-dimensional feature vector from LEAKGUARD_SPEC.md section 6.

Every feature is deterministic and cheap: the same commit SHA must always
produce the same vector, and therefore the same verdict. Nothing here consults
a model, the network, or the clock.

The vector feeds a logistic regression, so each dimension has to stay
individually explainable — the report prints one evidence line per non-zero
contribution, and the counterfactual ("confidence would drop to X if the site
were wrapped in `with`") is just this vector with one entry flipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from .detector import ModuleAnalysis, OpenSite, analyse_module, is_route_decorated
from .registry import suggests_close

#: Order is part of the on-disk contract for `model.json`. Append only.
FEATURE_NAMES: Sequence[str] = (
    "leaking_path_fraction",        # 0-1: exit paths with no close / paths that opened
    "escapes_return",               # handle handed back to the caller
    "escapes_self_attr",            # stored on self / an object attribute
    "escapes_container",            # appended to a list, dict, queue, ...
    "escapes_call_arg",             # passed to a call we cannot resolve
    "callee_closes_param",          # in-module summary says the callee releases it
    "close_present_but_unguarded",  # a close exists, but not in finally / with
    "in_loop",                      # acquisition inside for/while: fd exhaustion
    "raising_call_between",         # something that can raise sits open..close
    "reassigned_before_close",      # handle rebound, orphaning this acquisition
    "resource_type_weight",         # registry blast-radius weight
    "is_test_or_script_file",       # test_*.py / conftest.py / __main__ script
    "is_async_resource",            # needs await / async with
    "callee_name_suggests_close",   # passed to *close*/*shutdown*/*cleanup*/...
)

#: Multipliers for `risk = P(leak) x exposure` (spec section 8). Kept next to
#: the features because they are computed from the same `OpenSite`.
EXPOSURE_IN_LOOP = 2.0
EXPOSURE_ROUTE = 2.8
EXPOSURE_ASYNC = 1.2


@dataclass(frozen=True)
class FeatureVector:
    site: OpenSite
    values: Dict[str, float]

    def as_list(self) -> List[float]:
        return [float(self.values[name]) for name in FEATURE_NAMES]

    @property
    def exposure(self) -> float:
        """Blast radius, independent of P(leak)."""
        multiplier = float(self.site.weight)
        if self.site.in_loop:
            multiplier *= EXPOSURE_IN_LOOP
        if is_route_decorated(self.site.decorators):
            multiplier *= EXPOSURE_ROUTE
        if self.site.is_async:
            multiplier *= EXPOSURE_ASYNC
        return round(multiplier, 4)


def extract(site: OpenSite) -> FeatureVector:
    escapes = site.outcome.escape_kinds
    values: Dict[str, float] = {
        "leaking_path_fraction": round(site.outcome.leaking_fraction, 6),
        "escapes_return": float("return" in escapes),
        "escapes_self_attr": float("self_attr" in escapes),
        "escapes_container": float("container" in escapes),
        "escapes_call_arg": float("call_arg" in escapes),
        "callee_closes_param": float(site.callee_closes_param),
        "close_present_but_unguarded": float(
            site.outcome.closed_anywhere and not site.close_guarded
        ),
        "in_loop": float(site.in_loop),
        "raising_call_between": float(site.outcome.raising_call_between),
        "reassigned_before_close": float(site.outcome.orphaned_by_reassign > 0),
        "resource_type_weight": float(site.weight),
        "is_test_or_script_file": float(site.is_test_or_script),
        "is_async_resource": float(site.is_async),
        "callee_name_suggests_close": float(
            any(suggests_close(callee) for callee in site.escape_callees)
        ),
    }
    missing = set(FEATURE_NAMES) - set(values)
    if missing:  # guards against a rename desynchronising model.json
        raise AssertionError("feature vector missing: %s" % sorted(missing))
    return FeatureVector(site=site, values=values)


def extract_module(source: str, filename: str) -> List[FeatureVector]:
    analysis: ModuleAnalysis = analyse_module(source, filename)
    if analysis.parse_error:
        return []
    return [extract(site) for site in analysis.sites]


def describe(vector: FeatureVector) -> List[str]:
    """Human-readable evidence lines, for the explainable report."""
    site = vector.site
    outcome = site.outcome
    lines: List[str] = []
    if outcome.total:
        lines.append(
            "%d of %d exit paths reach an exit without close"
            % (outcome.leaking, outcome.total)
        )
    if outcome.orphaned_by_reassign:
        lines.append("handle rebound before close, orphaning this acquisition")
    if site.in_loop:
        lines.append("acquisition inside a loop: descriptor exhaustion risk")
    if outcome.raising_call_between:
        lines.append("a call that can raise sits between open and close")
    if vector.values["close_present_but_unguarded"]:
        lines.append("close exists but is not wrapped in finally/with")
    for kind in sorted(outcome.escape_kinds):
        lines.append("handle escapes via %s" % kind)
    if site.class_closes_attr:
        lines.append("enclosing class releases this attribute in its closer")
    elif site.is_owned_attribute:
        lines.append("no method of %s ever releases this attribute" % site.class_name)
    if site.callee_closes_param:
        lines.append("callee summary shows the parameter is closed")
    return lines
