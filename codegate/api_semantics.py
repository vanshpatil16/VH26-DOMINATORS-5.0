"""API Semantics Resolver module for LeakGuard External API Resource Semantics.

Orchestrates resources.yaml lookup, contract validation, and LLM fallback.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from .knowledge_base import APIContract, KnowledgeBase
from .llm_resolver import LLMResolver, get_llm_config
from .validator import validate_contract

logger = logging.getLogger(__name__)


class APISemanticsResolver:
    """Resolves external API resource semantics using KB lookup + validated LLM fallback."""

    def __init__(
        self,
        kb: KnowledgeBase | None = None,
        llm_resolver: LLMResolver | None = None,
        min_confidence: float | None = None,
    ) -> None:
        self.kb = kb or KnowledgeBase()
        self.llm_resolver = llm_resolver or LLMResolver()
        cfg = get_llm_config()
        self.min_confidence = min_confidence if min_confidence is not None else cfg["min_confidence"]

    def parse_call_name(self, call_name: str) -> tuple[str, str]:
        """Split a dotted call name like 'some_library.process' into ('some_library', 'process')."""
        if "." in call_name:
            parts = call_name.rsplit(".", 1)
            return parts[0], parts[1]
        return "builtins", call_name

    def resolve_call(
        self, call_name: str, resource_type: str = "FILE", source_context: str = ""
    ) -> APIContract:
        """Resolve contract for a call name.

        Order:
        1. Check resources.yaml KnowledgeBase
        2. If unknown, invoke LLM fallback
        3. Validate contract
        4. If valid & meets min_confidence, persist to resources.yaml & return
        5. If unresolved, return UNKNOWN contract
        """
        library, function = self.parse_call_name(call_name)

        # 1. Knowledge Base Lookup
        kb_contract = self.kb.lookup(library, function, resource_type)
        if kb_contract is not None:
            return kb_contract

        # 2. LLM Fallback Resolution
        if not self.llm_resolver.is_available():
            logger.info(f"LLM API key not configured. Cannot resolve unknown API '{call_name}'.")
            return APIContract(
                library=library,
                function=function,
                resource_type=resource_type,
                behavior="UNKNOWN",
                ownership="UNKNOWN",
                confidence=0.0,
                reason="External API knowledge unavailable: LLM API key not configured.",
            )

        raw_dict = self.llm_resolver.resolve_api_semantics(
            library=library,
            function=function,
            resource_type=resource_type,
            source_context=source_context,
        )

        if not raw_dict:
            return APIContract(
                library=library,
                function=function,
                resource_type=resource_type,
                behavior="UNKNOWN",
                ownership="UNKNOWN",
                confidence=0.0,
                reason="External API behavior could not be verified by LLM.",
            )

        # 3. Validation
        is_valid, reason, validated_contract = validate_contract(
            raw_dict, min_confidence=self.min_confidence
        )

        if is_valid and validated_contract is not None:
            # 4. Safe Knowledge Base Update
            self.kb.save_contract(validated_contract)
            return validated_contract

        logger.info(f"API contract validation failed for '{call_name}': {reason}")
        return APIContract(
            library=library,
            function=function,
            resource_type=resource_type,
            behavior="UNKNOWN",
            ownership="UNKNOWN",
            confidence=0.0,
            reason=f"Validation failed: {reason}",
        )
