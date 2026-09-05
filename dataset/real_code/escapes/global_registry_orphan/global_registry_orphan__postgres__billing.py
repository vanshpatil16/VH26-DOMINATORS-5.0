"""Module-level registry nothing ever shuts down."""

import psycopg2


_REGISTRY = {}


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    _REGISTRY[key] = connection
    payload = connection.cursor()
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
