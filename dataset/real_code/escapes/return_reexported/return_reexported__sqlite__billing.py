"""Factory return passed straight back out, still unreleased."""

import sqlite3


def _acquire_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    return connection


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_sqlite(path, host, port)
    payload = connection.execute(query).fetchall()
    return connection
