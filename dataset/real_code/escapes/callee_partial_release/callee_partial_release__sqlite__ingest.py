"""Callee releases the handle on one branch only."""

import sqlite3


def _maybe_release(connection, flag=False):
    if flag:
        connection.close()


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    payload = connection.execute(query).fetchall()
    _maybe_release(connection, flag)
    return payload
