"""Configurable resource definitions for CodeGate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ResourceSpec:
    """One acquire → release pair."""

    # Acquire API canonical dotted name (matched against resolved call names)
    # Examples: "open", "socket.socket", "tempfile.NamedTemporaryFile", "sqlite3.connect"
    acquire: str
    # Primary release method name (called as <handle>.method())
    release: str = "close"
    # Additional release methods that count (e.g. Popen: wait, kill, terminate)
    alt_releases: list[str] = field(default_factory=list)
    # Kind: "call" = function call acquire, "method" = release is method on handle
    kind: str = "call"

    # Optional: treat `return <handle>` as ownership transfer (not leak)
    ownership_transferred_on_return: bool = True
    # Optional: treat passing handle to these functions as transfer
    transfer_via_calls: list[str] = field(default_factory=list)
    # True when synthesized by the duck-type fallback (in-memory inference,
    # never persisted). Findings from inferred specs report at `potential`.
    inferred: bool = False

    def matches_acquire(self, call_name: str) -> bool:
        """Canonical or suffix match (canonical names come from import resolution)."""
        return (
            call_name == self.acquire
            or call_name.endswith("." + self.acquire)
            or self.acquire.endswith("." + call_name)
        )

    def is_release_method(self, method: str) -> bool:
        return method == self.release or method in self.alt_releases


@dataclass
class CodeGateConfig:
    resources: list[ResourceSpec] = field(default_factory=list)
    # If True, `with open(...) as f:` is automatically safe (no analysis needed)
    with_is_safe: bool = True
    # If True, `try: ... finally: f.close()` is safe
    try_finally_is_safe: bool = True
    # HARDEN-3: if True, flag acquires where an uncaught exception (may-throw
    # call) leaks the resource even though normal paths are safe.
    # The classic `f = open(p); f.read(); f.close()` without try/finally.
    exception_safety: bool = True
    # Path to external API knowledge base resources.yaml
    kb_path: str | None = None
    # Path to a user-defined rules YAML file (explicit override).
    # When None, `.codegate/rules.yaml` under the cwd is auto-loaded if present.
    user_rules_path: str | None = None
    # Minimum confidence threshold for auto-persisting LLM resolved API contracts
    min_confidence: float = 0.85

    @classmethod
    def default(cls) -> "CodeGateConfig":
        return cls(
            resources=[
                # ── files ──────────────────────────────────────────────
                ResourceSpec(acquire="open", release="close"),
                ResourceSpec(acquire="io.open", release="close"),
                ResourceSpec(acquire="tempfile.NamedTemporaryFile", release="close"),
                ResourceSpec(acquire="tempfile.TemporaryFile", release="close"),
                ResourceSpec(acquire="tempfile.TemporaryDirectory", release="cleanup"),
                # ── sockets / network ──────────────────────────────────
                ResourceSpec(acquire="socket.socket", release="close"),
                ResourceSpec(acquire="socket.create_connection", release="close"),
                ResourceSpec(acquire="socket.socketpair", release="close"),
                # ── databases ──────────────────────────────────────────
                ResourceSpec(acquire="sqlite3.connect", release="close"),
                ResourceSpec(acquire="psycopg2.connect", release="close"),
                ResourceSpec(acquire="psycopg.connect", release="close"),
                ResourceSpec(acquire="pymysql.connect", release="close"),
                ResourceSpec(acquire="mysql.connector.connect", release="close"),
                ResourceSpec(acquire="pymongo.MongoClient", release="close"),
                # ── http clients ───────────────────────────────────────
                ResourceSpec(acquire="requests.Session", release="close"),
                ResourceSpec(acquire="httpx.Client", release="close"),
                ResourceSpec(acquire="httpx.AsyncClient", release="aclose"),
                # ── processes ──────────────────────────────────────────
                ResourceSpec(
                    acquire="subprocess.Popen",
                    release="wait",
                    alt_releases=["kill", "terminate", "poll"],
                ),
                ResourceSpec(
                    acquire="multiprocessing.Process",
                    release="join",
                    alt_releases=["terminate", "kill"],
                ),
                # ── stdlib high-frequency (batch 1) ──────────────────────
                ResourceSpec(acquire="os.fdopen", release="close"),
                ResourceSpec(acquire="mmap.mmap", release="close"),
                ResourceSpec(acquire="ftplib.FTP", release="close", alt_releases=["quit"]),
                ResourceSpec(acquire="smtplib.SMTP", release="close", alt_releases=["quit"]),
                ResourceSpec(acquire="smtplib.SMTP_SSL", release="close", alt_releases=["quit"]),
                ResourceSpec(acquire="telnetlib.Telnet", release="close"),
                ResourceSpec(acquire="select.poll", release="close"),
                ResourceSpec(acquire="selectors.DefaultSelector", release="close"),
                ResourceSpec(acquire="logging.FileHandler", release="close"),
                ResourceSpec(acquire="logging.RotatingFileHandler", release="close"),
                ResourceSpec(acquire="logging.TimedRotatingFileHandler", release="close"),
            ]
        )


DEFAULT_RESOURCES = CodeGateConfig.default().resources


def load_config_from_dict(d: dict) -> CodeGateConfig:
    resources = [ResourceSpec(**r) for r in d.get("resources", [])]
    return CodeGateConfig(
        resources=resources or CodeGateConfig.default().resources,
        with_is_safe=d.get("with_is_safe", True),
        try_finally_is_safe=d.get("try_finally_is_safe", True),
        exception_safety=d.get("exception_safety", True),
    )


USER_RULES_FILENAME = "rules.yaml"


def default_user_rules_path() -> str | None:
    """Project-local DSL file (`.codegate/rules.yaml` under cwd), if present."""
    cand = Path.cwd() / ".codegate" / USER_RULES_FILENAME
    return str(cand) if cand.is_file() else None


def normalize_user_rule(d: Any) -> ResourceSpec | None:
    """Tolerant single-rule parse. Accepts both schemas:

    - engine style:  {acquire: "acme.db.connect", release: "close", alt_releases: ["quit"]}
    - KB style:      {call: "acme.db.connect", type: "DATABASE", close: ["close", "quit"]}
    """
    if not isinstance(d, dict):
        return None
    acquire = d.get("acquire") or d.get("call")
    if not acquire or not isinstance(acquire, str):
        return None
    alt: list[str] = [str(a) for a in (d.get("alt_releases") or [])]
    release = d.get("release")
    if release is None:
        close = d.get("close", ["close"])
        if isinstance(close, str):
            close = [close]
        if not isinstance(close, list) or not close:
            return ResourceSpec(acquire=acquire, release="close", alt_releases=alt)
        primary = str(close[0])
        rest = [str(c) for c in close[1:]]
        alt = rest + [a for a in alt if a not in rest]
    else:
        primary = str(release)
    return ResourceSpec(acquire=acquire, release=primary, alt_releases=alt)


def load_user_rules(path: str | Path | None) -> list[ResourceSpec]:
    """Load user DSL rules. Accepts a top-level list or a `{resources: [...]}` mapping.
    Missing files, parse errors, and malformed entries yield no specs (never raise)."""
    if not path:
        return []
    p = Path(path)
    if not p.is_file():
        return []
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        items = data.get("resources", [])
    elif isinstance(data, list):
        items = data
    else:
        return []
    if not isinstance(items, list):
        return []
    specs: list[ResourceSpec] = []
    for item in items:
        spec = normalize_user_rule(item)
        if spec is not None and not any(s.matches_acquire(spec.acquire) for s in specs):
            specs.append(spec)
    return specs
