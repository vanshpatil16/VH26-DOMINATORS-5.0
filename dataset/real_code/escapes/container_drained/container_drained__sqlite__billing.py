"""Handles collected into a list the caller drains in a finally."""

import sqlite3


def _collect_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = sqlite3.connect(path)
        opened.append(connection)
    return opened


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_sqlite(path, host, port, items=items)
    try:
        for connection in opened:
            payload = connection.execute(query).fetchall()
    finally:
        for connection in opened:
            connection.close()
    return payload
