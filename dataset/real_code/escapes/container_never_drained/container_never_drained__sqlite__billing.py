"""Handles collected into a list nothing ever drains."""

import sqlite3


def _collect_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = sqlite3.connect(path)
        opened.append(connection)
    return opened


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_sqlite(path, host, port, items=items)
    for connection in opened:
        payload = connection.execute(query).fetchall()
    return payload
