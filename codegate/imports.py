"""Import tracking — resolve local names to canonical qualified names.

Production code imports resources under aliases:

    import sqlite3 as db          ->  db.connect(...)   ==  sqlite3.connect(...)
    from socket import socket     ->  socket(...)       ==  socket.socket(...)
    from psycopg2 import connect  ->  connect(...)      ==  psycopg2.connect(...)

Without this, CodeGate only suffix-matches and misses real findings.
"""

from __future__ import annotations

import ast
from typing import Optional

# Names the analyzer treats as builtins (never shadow-resolved through imports
# unless actually imported — the map wins if a module re-exports them).
_BUILTIN_CALLS = {"open"}


def build_import_map(tree: ast.AST) -> dict[str, str]:
    """local name -> canonical dotted path ('db' -> 'sqlite3')."""
    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    imports[a.asname] = a.name
                else:
                    # `import a.b.c` binds `a`
                    top = a.name.split(".")[0]
                    imports[top] = top
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for a in node.names:
                if a.name == "*":
                    continue
                local = a.asname or a.name
                canonical = f"{mod}.{a.name}" if mod else a.name
                imports[local] = canonical
    return imports


def resolve_call_name(call_name: str, import_map: dict[str, str] | None) -> str:
    """Resolve a dotted call name through the import map.

    's.socket' with {'s': 'socket'}              -> 'socket.socket'
    'connect'    with {'connect': 'psycopg2.connect'} -> 'psycopg2.connect'
    'open'       (not in map, builtin)           -> 'open'
    Unknown heads pass through unchanged (may be locals/attributes).
    """
    if not import_map:
        return call_name
    if "." in call_name:
        head, rest = call_name.split(".", 1)
    else:
        head, rest = call_name, ""
    if head in import_map:
        canon = import_map[head]
        return f"{canon}.{rest}" if rest else canon
    return call_name
