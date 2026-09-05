"""Knowledge Base module for LeakGuard External API Resource Semantics.

Loads, queries, updates, and atomically persists API resource contracts in resources.yaml.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class APIContract:
    """Structured contract describing the resource lifecycle semantics of an API function."""

    library: str
    function: str
    resource_type: str = "FILE"
    behavior: str = "UNKNOWN"
    ownership: str = "UNKNOWN"
    exception_safety: str = "UNKNOWN"  # "GUARANTEED" | "NOT_GUARANTEED" | "UNKNOWN"
    confidence: float = 0.0
    evidence: str = ""
    source: str = ""
    discovered_by: str = "kb"  # "kb" | "llm" | "manual"
    version: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> APIContract:
        return cls(
            library=str(d.get("library", "")),
            function=str(d.get("function", "")),
            resource_type=str(d.get("resource_type", "FILE")),
            behavior=str(d.get("behavior", "UNKNOWN")),
            ownership=str(d.get("ownership", "UNKNOWN")),
            exception_safety=str(d.get("exception_safety", "UNKNOWN")),
            confidence=float(d.get("confidence", 0.0)),
            evidence=str(d.get("evidence", "")),
            source=str(d.get("source", "")),
            discovered_by=str(d.get("discovered_by", "kb")),
            version=str(d.get("version", "")),
            reason=str(d.get("reason", "")),
        )


class KnowledgeBase:
    """Manages resources.yaml loading, lookup, and safe atomic updates."""

    def __init__(self, kb_path: str | Path | None = None) -> None:
        self.kb_path = Path(kb_path) if kb_path else self._default_path()
        self.resources: list[dict[str, Any]] = []
        self.contracts: list[APIContract] = []
        self.load()

    @staticmethod
    def _default_path() -> Path:
        cwd = Path.cwd()
        candidates = [
            cwd / "codegate" / "resources.yaml",
            cwd / "leakguard" / "resources.yaml",
            cwd / "resources.yaml",
        ]
        for cand in candidates:
            if cand.exists():
                return cand
        return candidates[0]

    def load(self) -> None:
        """Load resources.yaml cleanly. Handles missing or corrupted files gracefully."""
        if not self.kb_path.exists():
            self.resources = []
            self.contracts = []
            return

        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            if not isinstance(data, dict):
                logger.warning("Corrupted resources.yaml: root is not a mapping. Starting with empty KB.")
                self.resources = []
                self.contracts = []
                return

            self.resources = data.get("resources", []) or []
            raw_contracts = data.get("api_contracts", []) or []
            self.contracts = [APIContract.from_dict(c) for c in raw_contracts if isinstance(c, dict)]
        except Exception as e:
            logger.warning(f"Failed to parse resources.yaml ({e}). Falling back to empty KB.")
            self.resources = []
            self.contracts = []

    def lookup(
        self, library: str, function: str, resource_type: str | None = None
    ) -> Optional[APIContract]:
        """Fast, deterministic lookup for known API contract."""
        for contract in self.contracts:
            if contract.library == library and contract.function == function:
                if (
                    resource_type is None
                    or not contract.resource_type
                    or contract.resource_type.upper() == resource_type.upper()
                    or (resource_type.upper() in ("FILE", "SOCKET", "DATABASE", "DB", "HTTP", "PROCESS"))
                ):
                    return contract
        return None

    def save_contract(self, contract: APIContract) -> bool:
        """Safely & atomically persist a validated APIContract into resources.yaml."""
        try:
            # Update existing matching entry or append new
            updated = False
            for i, c in enumerate(self.contracts):
                if c.library == contract.library and c.function == contract.function:
                    self.contracts[i] = contract
                    updated = True
                    break
            if not updated:
                self.contracts.append(contract)

            # Prepare data structure to write
            data = {
                "resources": self.resources,
                "api_contracts": [c.to_dict() for c in self.contracts],
            }

            self.kb_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic file write via temporary file
            temp_fd, temp_path_str = tempfile.mkstemp(
                dir=self.kb_path.parent, prefix="kb_resources_", suffix=".yaml"
            )
            temp_path = Path(temp_path_str)
            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, sort_keys=False, default_flow_style=False)
                # Atomic replace
                temp_path.replace(self.kb_path)
                return True
            except Exception as inner_e:
                logger.error(f"Failed writing temp KB file: {inner_e}")
                if temp_path.exists():
                    os.unlink(temp_path)
                return False
        except Exception as e:
            logger.error(f"Failed to persist API contract to {self.kb_path}: {e}")
            return False
