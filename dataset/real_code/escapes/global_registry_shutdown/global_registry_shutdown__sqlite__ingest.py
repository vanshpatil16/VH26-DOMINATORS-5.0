"""Module-level registry with a shutdown that releases every entry."""

import sqlite3


_REGISTRY = {}


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    _REGISTRY[key] = connection
    payload = connection.execute(query).fetchall()
    return payload


def shutdown():
    for connection in _REGISTRY.values():
        connection.close()
    _REGISTRY.clear()
