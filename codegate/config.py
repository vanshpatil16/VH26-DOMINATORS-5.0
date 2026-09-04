"""Configurable resource definitions for CodeGate."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResourceSpec:
    """One acquire → release pair."""

    # Acquire API fully-qualified or simple name (matched against Call func)
    # Examples: "open", "socket.socket", "tempfile.NamedTemporaryFile", "sqlite3.connect"
    acquire: str
    # Release method name (called as <handle>.method())
    # Examples: "close", "release", "disconnect", "__exit__"
    release: str = "close"
    # Kind: "call" = function call acquire, "method" = release is method on handle
    kind: str = "call"

    # Optional: treat `return <handle>` as ownership transfer (not leak)
    ownership_transferred_on_return: bool = True
    # Optional: treat passing handle to these functions as transfer
    transfer_via_calls: list[str] = field(default_factory=list)

    def matches_acquire(self, call_name: str) -> bool:
        """Simple match: exact or suffix (so socket.socket matches 'socket.socket' and 'socket')."""
        return call_name == self.acquire or call_name.endswith("." + self.acquire) or self.acquire.endswith("." + call_name)


@dataclass
class CodeGateConfig:
    resources: list[ResourceSpec] = field(default_factory=list)
    # If True, `with open(...) as f:` is automatically safe (no analysis needed)
    with_is_safe: bool = True
    # If True, `try: ... finally: f.close()` is safe
    try_finally_is_safe: bool = True

    @classmethod
    def default(cls) -> "CodeGateConfig":
        return cls(
            resources=[
                ResourceSpec(acquire="open", release="close"),
                ResourceSpec(acquire="socket.socket", release="close"),
                ResourceSpec(acquire="socket.create_connection", release="close"),
                ResourceSpec(acquire="tempfile.NamedTemporaryFile", release="close"),
                ResourceSpec(acquire="tempfile.TemporaryFile", release="close"),
                ResourceSpec(acquire="sqlite3.connect", release="close"),
                ResourceSpec(acquire="open", release="close", transfer_via_calls=[]),
                # Generic file-like: io.open
                ResourceSpec(acquire="io.open", release="close"),
            ]
        )


DEFAULT_RESOURCES = CodeGateConfig.default().resources


def load_config_from_dict(d: dict) -> CodeGateConfig:
    resources = [ResourceSpec(**r) for r in d.get("resources", [])]
    return CodeGateConfig(
        resources=resources or CodeGateConfig.default().resources,
        with_is_safe=d.get("with_is_safe", True),
        try_finally_is_safe=d.get("try_finally_is_safe", True),
    )
