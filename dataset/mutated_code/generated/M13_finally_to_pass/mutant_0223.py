"""Cleanup delegated to a helper called on every path."""

import sqlite3


def _release(connection):
    connection.close()


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = sqlite3.connect(path)
    try:
        payload = connection.execute(query).fetchall()
        return payload
    finally:
        pass
