"""Module-level registry with a shutdown that releases every entry."""

import psycopg2


_REGISTRY = {}


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    _REGISTRY[key] = connection
    payload = connection.cursor()
    return payload


def shutdown():
    for connection in _REGISTRY.values():
        connection.close()
    _REGISTRY.clear()
