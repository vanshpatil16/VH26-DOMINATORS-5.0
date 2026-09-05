"""SQLite-backed knowledge base for LeakGuard external API resource semantics.

``resources.yaml`` remains the human-readable seed data. On first use its
contents are imported into a colocated SQLite database; all subsequent lookups
and validated contract updates use SQLite.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Optional

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
    exception_safety: str = "UNKNOWN"
    confidence: float = 0.0
    evidence: str = ""
    source: str = ""
    discovered_by: str = "kb"
    version: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "APIContract":
        return cls(
            library=str(data.get("library", "")),
            function=str(data.get("function", "")),
            resource_type=str(data.get("resource_type", "FILE")),
            behavior=str(data.get("behavior", "UNKNOWN")),
            ownership=str(data.get("ownership", "UNKNOWN")),
            exception_safety=str(data.get("exception_safety", "UNKNOWN")),
            confidence=float(data.get("confidence", 0.0)),
            evidence=str(data.get("evidence", "")),
            source=str(data.get("source", "")),
            discovered_by=str(data.get("discovered_by", "kb")),
            version=str(data.get("version", "")),
            reason=str(data.get("reason", "")),
        )


class KnowledgeBase:
    """SQLite KB service, with YAML retained strictly as its idempotent seed source.

    The public ``resources``, ``contracts``, ``lookup`` and ``save_contract``
    members remain unchanged so analyzer and LLM orchestration code remain
    independent of the persistence backend.
    """

    def __init__(
        self, kb_path: str | Path | None = None, db_path: str | Path | None = None
    ) -> None:
        self.kb_path = Path(kb_path) if kb_path else self._default_path()
        self.db_path = (
            Path(db_path)
            if db_path
            else self.kb_path.with_suffix(".sqlite3") if kb_path else self.kb_path.parent / "knowledge_base.sqlite3"
        )
        self.resources: list[dict[str, Any]] = []
        self.contracts: list[APIContract] = []
        self.load()

    @staticmethod
    def _default_path() -> Path:
        cwd = Path.cwd()
        candidates = [cwd / "codegate" / "resources.yaml", cwd / "leakguard" / "resources.yaml", cwd / "resources.yaml"]
        return next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a transaction and always close its SQLite file handle."""
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY,
                call_name TEXT NOT NULL UNIQUE,
                resource_type TEXT NOT NULL DEFAULT 'FILE',
                close_methods_json TEXT NOT NULL DEFAULT '[]',
                weight REAL,
                payload_json TEXT NOT NULL,
                seeded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS api_contracts (
                id INTEGER PRIMARY KEY,
                library TEXT NOT NULL,
                function TEXT NOT NULL,
                resource_type TEXT NOT NULL DEFAULT 'FILE',
                behavior TEXT NOT NULL DEFAULT 'UNKNOWN',
                ownership TEXT NOT NULL DEFAULT 'UNKNOWN',
                exception_safety TEXT NOT NULL DEFAULT 'UNKNOWN',
                confidence REAL NOT NULL DEFAULT 0.0,
                evidence TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                discovered_by TEXT NOT NULL DEFAULT 'kb',
                version TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                validation_status TEXT NOT NULL DEFAULT 'seeded',
                validated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(library, function)
            );
            CREATE INDEX IF NOT EXISTS idx_api_contracts_library_function ON api_contracts(library, function);
            CREATE INDEX IF NOT EXISTS idx_resources_call_name ON resources(call_name);
        """)

    def _read_seed(self) -> dict[str, Any]:
        if not self.kb_path.exists():
            return {}
        try:
            with self.kb_path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
            if not isinstance(data, dict):
                raise ValueError("root is not a mapping")
            return data
        except Exception as exc:
            logger.warning("Failed to parse resources.yaml (%s). Skipping seed import.", exc)
            return {}

    @staticmethod
    def _contract_values(contract: APIContract, status: str, timestamp: str) -> tuple[Any, ...]:
        return (
            contract.library, contract.function, contract.resource_type, contract.behavior,
            contract.ownership, contract.exception_safety, contract.confidence, contract.evidence,
            contract.source, contract.discovered_by, contract.version, contract.reason, status,
            timestamp if status == "validated" else None, timestamp, timestamp,
        )

    def _seed_from_yaml(self, connection: sqlite3.Connection) -> None:
        """Import missing YAML records; never overwrite learned SQLite knowledge."""
        data, now = self._read_seed(), self._now()
        for resource in data.get("resources", []) or []:
            if not isinstance(resource, dict) or not resource.get("call"):
                continue
            connection.execute("""
                INSERT OR IGNORE INTO resources
                    (call_name, resource_type, close_methods_json, weight, payload_json, seeded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(resource["call"]), str(resource.get("type", "FILE")),
                json.dumps(resource.get("close", [])), resource.get("weight"),
                json.dumps(resource, sort_keys=True), now,
            ))
        for raw in data.get("api_contracts", []) or []:
            if not isinstance(raw, dict):
                continue
            contract = APIContract.from_dict(raw)
            if not contract.library or not contract.function:
                continue
            connection.execute("""
                INSERT OR IGNORE INTO api_contracts (
                    library, function, resource_type, behavior, ownership, exception_safety,
                    confidence, evidence, source, discovered_by, version, reason,
                    validation_status, validated_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, self._contract_values(contract, "seeded", now))

    @staticmethod
    def _contract_from_row(row: sqlite3.Row) -> APIContract:
        return APIContract(
            library=row["library"], function=row["function"], resource_type=row["resource_type"],
            behavior=row["behavior"], ownership=row["ownership"], exception_safety=row["exception_safety"],
            confidence=row["confidence"], evidence=row["evidence"], source=row["source"],
            discovered_by=row["discovered_by"], version=row["version"], reason=row["reason"],
        )

    def load(self) -> None:
        """Initialize SQLite, run the safe seed migration, and refresh cached views."""
        try:
            with self._connection() as connection:
                self._create_schema(connection)
                self._seed_from_yaml(connection)
                self.resources = [json.loads(row["payload_json"]) for row in connection.execute(
                    "SELECT payload_json FROM resources ORDER BY id"
                )]
                self.contracts = [self._contract_from_row(row) for row in connection.execute(
                    "SELECT * FROM api_contracts ORDER BY id"
                )]
        except sqlite3.Error as exc:
            logger.warning("Failed to initialize SQLite knowledge base (%s).", exc)
            self.resources, self.contracts = [], []

    def lookup_resource(self, call_name: str) -> Optional[dict[str, Any]]:
        """Look up a resource definition by fully-qualified acquisition call."""
        try:
            with self._connection() as connection:
                row = connection.execute("SELECT payload_json FROM resources WHERE call_name = ?", (call_name,)).fetchone()
            return json.loads(row["payload_json"]) if row else None
        except sqlite3.Error as exc:
            logger.warning("SQLite resource lookup failed: %s", exc)
            return None

    def lookup_api_contract(self, library: str, function: str, resource_type: str | None = None) -> Optional[APIContract]:
        """Look up a contract using the indexed ``library`` + ``function`` key."""
        try:
            with self._connection() as connection:
                row = connection.execute("SELECT * FROM api_contracts WHERE library = ? AND function = ?", (library, function)).fetchone()
            if row is None:
                return None
            contract = self._contract_from_row(row)
            if (resource_type is None or not contract.resource_type or
                    contract.resource_type.upper() == resource_type.upper() or
                    resource_type.upper() in ("FILE", "SOCKET", "DATABASE", "DB", "HTTP", "PROCESS")):
                return contract
            return None
        except sqlite3.Error as exc:
            logger.warning("SQLite API contract lookup failed: %s", exc)
            return None

    def lookup(self, library: str, function: str, resource_type: str | None = None) -> Optional[APIContract]:
        """Backward-compatible alias for :meth:`lookup_api_contract`."""
        return self.lookup_api_contract(library, function, resource_type)

    def add_api_contract(self, contract: APIContract) -> bool:
        """Persist a contract that has passed the caller's validation process."""
        return self.update_api_contract(contract)

    def update_api_contract(self, contract: APIContract) -> bool:
        """Upsert a validated contract without changing the YAML seed file."""
        try:
            now = self._now()
            with self._connection() as connection:
                self._create_schema(connection)
                connection.execute("""
                    INSERT INTO api_contracts (
                        library, function, resource_type, behavior, ownership, exception_safety,
                        confidence, evidence, source, discovered_by, version, reason,
                        validation_status, validated_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(library, function) DO UPDATE SET
                        resource_type=excluded.resource_type, behavior=excluded.behavior,
                        ownership=excluded.ownership, exception_safety=excluded.exception_safety,
                        confidence=excluded.confidence, evidence=excluded.evidence, source=excluded.source,
                        discovered_by=excluded.discovered_by, version=excluded.version, reason=excluded.reason,
                        validation_status=excluded.validation_status, validated_at=excluded.validated_at,
                        updated_at=excluded.updated_at
                """, self._contract_values(contract, "validated", now))
            self.contracts = [item for item in self.contracts if (item.library, item.function) != (contract.library, contract.function)]
            self.contracts.append(contract)
            return True
        except sqlite3.Error as exc:
            logger.error("Failed to persist validated API contract to %s: %s", self.db_path, exc)
            return False

    def save_contract(self, contract: APIContract) -> bool:
        """Backward-compatible validated-contract persistence entry point."""
        return self.update_api_contract(contract)
