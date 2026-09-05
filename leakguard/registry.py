"""Resource registry: the deterministic answer to "what is a resource?".

The registry is data, never a prediction. `resources.yaml` is the single source
of truth; it is parsed with PyYAML when available and otherwise with a tiny
flow-mapping parser so that LeakGuard keeps a zero-dependency install.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources.yaml")

# Attribute names that count as "closing" regardless of the resource family.
# Kept small on purpose: a generous list here silently destroys recall.
GENERIC_CLOSERS = ("close", "release", "shutdown", "terminate", "kill", "cleanup", "dispose")

# Helper-function names that strongly imply the callee takes over cleanup.
CLOSER_NAME_RE = re.compile(
    r"(^|_)(close|shutdown|cleanup|clean_up|release|dispose|teardown|tear_down"
    r"|finalize|destroy|free|quit)($|_)",
    re.IGNORECASE,
)

_QUOTE_CHARS = ('"', "'")


@dataclass(frozen=True)
class ResourceSpec:
    """One registry entry."""

    call: str
    type: str
    close: Tuple[str, ...]
    weight: float = 1.0
    is_async: bool = False
    # Does `with <acquire>() as x:` actually release the resource?
    # False for DBAPI connections: `with sqlite3.connect(p) as conn` is a
    # *transaction* context manager and leaves the connection open. This single
    # flag is one of the highest-value edge cases in the whole registry.
    ctx_closes: bool = True
    # Some resources are not acquired by their constructor. `threading.Lock()`
    # allocates nothing; the acquisition is `lock.acquire()` and the release is
    # `lock.release()`. Entries with `acquired_by` set are never matched as
    # constructor open-sites.
    acquired_by: str = ""

    @property
    def base_name(self) -> str:
        return self.call.rsplit(".", 1)[-1]


# --------------------------------------------------------------------------- #
# YAML loading
# --------------------------------------------------------------------------- #

_FLOW_ENTRY_RE = re.compile(r"^\s*-\s*\{(?P<body>.*)\}\s*$")


def _coerce(token: str):
    token = token.strip()
    if not token:
        return None
    if token[0] in _QUOTE_CHARS and token[-1] == token[0]:
        return token[1:-1]
    if token.startswith("["):
        inner = token[1:-1]
        return [_coerce(p) for p in _split_top_level(inner)] if inner.strip() else []
    low = token.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none", "~"):
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token


def _split_top_level(text: str) -> List[str]:
    """Split on commas that are not nested inside brackets or quotes."""
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    quote = ""
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in _QUOTE_CHARS:
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def _parse_minimal_yaml(text: str) -> List[dict]:
    """Parse the `resources:` list of flow mappings used by resources.yaml."""
    entries: List[dict] = []
    for raw in text.splitlines():
        if raw.lstrip().startswith("#"):
            continue
        match = _FLOW_ENTRY_RE.match(raw)
        if not match:
            continue
        record: dict = {}
        for pair in _split_top_level(match.group("body")):
            if ":" not in pair:
                continue
            key, _, value = pair.partition(":")
            record[key.strip()] = _coerce(value)
        if record.get("call"):
            entries.append(record)
    return entries


def load_specs(path: str = REGISTRY_PATH) -> List[ResourceSpec]:
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    records: Optional[List[dict]] = None
    try:  # PyYAML is optional; the mini-parser handles our own file fine.
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict) and isinstance(loaded.get("resources"), list):
            records = loaded["resources"]
    except Exception:
        records = None
    if records is None:
        records = _parse_minimal_yaml(text)
    specs = []
    for rec in records:
        specs.append(
            ResourceSpec(
                call=str(rec["call"]),
                type=str(rec.get("type", "UNKNOWN")),
                close=tuple(rec.get("close") or ("close",)),
                weight=float(rec.get("weight", 1.0)),
                is_async=bool(rec.get("async", False)),
                ctx_closes=bool(rec.get("ctx_closes", True)),
                acquired_by=str(rec.get("acquired_by") or ""),
            )
        )
    return specs


@dataclass
class Registry:
    specs: List[ResourceSpec] = field(default_factory=load_specs)

    def __post_init__(self) -> None:
        self.by_call: Dict[str, ResourceSpec] = {s.call: s for s in self.specs}
        # Suffix index: `sk.socket` matches the `socket.socket` entry once `sk`
        # has been resolved back to `socket` by the import resolver.
        self.by_tail: Dict[str, List[ResourceSpec]] = {}
        for spec in self.specs:
            self.by_tail.setdefault(spec.base_name, []).append(spec)

    def lookup(self, dotted: str) -> Optional[ResourceSpec]:
        if dotted in self.by_call:
            return self.by_call[dotted]
        # `pkg.vendor.socket.socket` -> try progressively shorter suffixes, but
        # only ever match a DOTTED entry. Without that guard `valve.open()` on a
        # domain object matches the builtin `open` entry — a false positive the
        # adversarial corpus catches immediately.
        parts = dotted.split(".")
        for start in range(1, len(parts) - 1):
            candidate = ".".join(parts[start:])
            if candidate in self.by_call:
                return self.by_call[candidate]
        return None

    def closers_for(self, spec: Optional[ResourceSpec]) -> Tuple[str, ...]:
        return spec.close if spec else GENERIC_CLOSERS

    @property
    def types(self) -> List[str]:
        return sorted({s.type for s in self.specs})

    @property
    def all_closers(self) -> Tuple[str, ...]:
        """Every release verb any registered resource uses.

        Used as the fallback when the handle has no known spec -- a function
        parameter, for instance -- so that a helper calling process.wait() on
        its argument still registers as releasing a subprocess.
        """
        verbs = set(GENERIC_CLOSERS)
        for spec in self.specs:
            verbs.update(spec.close)
        return tuple(sorted(verbs))


DEFAULT_REGISTRY = Registry()


# --------------------------------------------------------------------------- #
# Import alias resolution
# --------------------------------------------------------------------------- #


class ImportResolver(ast.NodeVisitor):
    """Maps local binding names back to their canonical dotted names.

    Handles `import socket as sk`, `from sqlite3 import connect`, and
    `from contextlib import closing as _closing`.
    """

    def __init__(self) -> None:
        self.aliases: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local = alias.asname or alias.name.split(".")[0]
            target = alias.name if alias.asname else alias.name.split(".")[0]
            self.aliases[local] = target
            if not alias.asname:
                self.aliases[alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local = alias.asname or alias.name
            self.aliases[local] = f"{module}.{alias.name}" if module else alias.name
        self.generic_visit(node)

    def resolve(self, dotted: str) -> str:
        parts = dotted.split(".")
        head = self.aliases.get(parts[0])
        if head is None:
            return dotted
        return ".".join([head] + parts[1:])


def dotted_name(node: ast.AST) -> Optional[str]:
    """Return the dotted source text of a Name/Attribute chain, else None."""
    parts: List[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def collect_aliases(tree: ast.AST) -> ImportResolver:
    resolver = ImportResolver()
    resolver.visit(tree)
    return resolver


def suggests_close(name: str) -> bool:
    """True when a callee name implies it performs cleanup on its argument."""
    return bool(CLOSER_NAME_RE.search(name.rsplit(".", 1)[-1]))


def iter_specs(registry: Registry = DEFAULT_REGISTRY) -> Iterable[ResourceSpec]:
    return iter(registry.specs)
