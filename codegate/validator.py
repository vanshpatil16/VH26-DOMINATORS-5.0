"""Contract Validation module for LeakGuard External API Resource Semantics.

Validates candidate APIContracts returned by LLM or external sources before persistence.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .knowledge_base import APIContract

logger = logging.getLogger(__name__)

ALLOWED_BEHAVIORS = {
    "CLOSES_INPUT",
    "PRESERVES_INPUT",
    "CREATES_RESOURCE",
    "RETURNS_RESOURCE",
    "TRANSFERS_OWNERSHIP",
    "CONDITIONAL_CLOSE",
    "UNKNOWN",
}

ALLOWED_OWNERSHIPS = {
    "BORROW",
    "CONSUME",
    "TRANSFER",
    "RETURN",
    "UNKNOWN",
}

ALLOWED_EXCEPTION_SAFETY = {
    "GUARANTEED",
    "NOT_GUARANTEED",
    "UNKNOWN",
}

IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$")


def validate_contract(
    raw_data: dict[str, Any] | APIContract, min_confidence: float = 0.85
) -> tuple[bool, str, APIContract | None]:
    """Validate candidate API contract against strict schema and confidence constraints.

    Returns:
        (is_valid: bool, reason: str, contract: APIContract | None)
    """
    if isinstance(raw_data, APIContract):
        contract_dict = raw_data.to_dict()
    elif isinstance(raw_data, dict):
        contract_dict = raw_data
    else:
        return False, "Input data is neither a dict nor APIContract instance.", None

    library = str(contract_dict.get("library", "")).strip()
    function = str(contract_dict.get("function", "")).strip()

    if not library or not function:
        return False, "Missing required fields 'library' or 'function'.", None

    if not IDENTIFIER_PATTERN.match(library):
        return False, f"Invalid library identifier format: '{library}'.", None

    if not IDENTIFIER_PATTERN.match(function):
        return False, f"Invalid function identifier format: '{function}'.", None

    raw_behavior = str(contract_dict.get("behavior", "")).strip().upper()
    behavior = raw_behavior
    if behavior not in ALLOWED_BEHAVIORS:
        # Fallback: extract any valid behavior token from composite/piped response
        tokens = [t.strip() for t in re.split(r"[|/,;\s]+", raw_behavior) if t.strip()]
        matched = False
        for tok in tokens:
            if tok in ALLOWED_BEHAVIORS:
                behavior = tok
                matched = True
                break
        if not matched:
            return False, f"Invalid behavior '{raw_behavior}'. Allowed: {sorted(ALLOWED_BEHAVIORS)}", None

    raw_ownership = str(contract_dict.get("ownership", "")).strip().upper()
    ownership = raw_ownership
    if ownership not in ALLOWED_OWNERSHIPS:
        tokens = [t.strip() for t in re.split(r"[|/,;\s]+", raw_ownership) if t.strip()]
        matched = False
        for tok in tokens:
            if tok in ALLOWED_OWNERSHIPS:
                ownership = tok
                matched = True
                break
        if not matched:
            return False, f"Invalid ownership '{raw_ownership}'. Allowed: {sorted(ALLOWED_OWNERSHIPS)}", None

    raw_exc = str(contract_dict.get("exception_safety", "UNKNOWN")).strip().upper()
    exception_safety = raw_exc
    if exception_safety not in ALLOWED_EXCEPTION_SAFETY:
        tokens = [t.strip() for t in re.split(r"[|/,;\s]+", raw_exc) if t.strip()]
        matched = False
        for tok in tokens:
            if tok in ALLOWED_EXCEPTION_SAFETY:
                exception_safety = tok
                matched = True
                break
        if not matched:
            exception_safety = "UNKNOWN"

    try:
        confidence = float(contract_dict.get("confidence", 0.0))
    except (ValueError, TypeError):
        return False, "Field 'confidence' must be a numeric float.", None

    if not (0.0 <= confidence <= 1.0):
        return False, f"Confidence {confidence} out of range [0.0, 1.0].", None

    if confidence < min_confidence:
        return (
            False,
            f"Confidence {confidence:.2f} is below minimum required threshold {min_confidence:.2f}.",
            None,
        )

    contract = APIContract(
        library=library,
        function=function,
        resource_type=str(contract_dict.get("resource_type", "FILE")).upper(),
        behavior=behavior,
        ownership=ownership,
        exception_safety=exception_safety,
        confidence=confidence,
        evidence=str(contract_dict.get("evidence", "")),
        source=str(contract_dict.get("source", "")),
        discovered_by=str(contract_dict.get("discovered_by", "llm")),
        version=str(contract_dict.get("version", "")),
        reason=str(contract_dict.get("reason", "")),
    )

    return True, "Valid", contract
