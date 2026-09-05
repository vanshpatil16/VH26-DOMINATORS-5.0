"""Factory hands ownership to a caller that closes it."""

import contextlib
import sqlite3


def _acquire_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    return connection


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_sqlite(path, host, port)) as connection:
        payload = connection.execute(query).fetchall()
    return payload
