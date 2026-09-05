"""Collected handles released by a named cleanup helper."""

import sqlite3


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = sqlite3.connect(path)
        opened.append(connection)
    return opened


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_sqlite(path, host, port, items=items)
    try:
        for connection in opened:
            payload = connection.execute(query).fetchall()
    finally:
        close_all(opened)
    return payload
