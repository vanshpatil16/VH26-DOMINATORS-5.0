"""Module-level registry nothing ever shuts down."""

import sqlite3


_REGISTRY = {}


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    _REGISTRY[key] = connection
    payload = connection.execute(query).fetchall()
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
