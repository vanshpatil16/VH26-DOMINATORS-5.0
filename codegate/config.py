"""Configurable resource definitions for CodeGate."""

from __future__ import annotations

from dataclasses import dataclass, field


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
