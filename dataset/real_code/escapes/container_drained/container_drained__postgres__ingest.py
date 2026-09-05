"""Handles collected into a list the caller drains in a finally."""

import psycopg2


def _collect_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = psycopg2.connect(dsn)
        opened.append(connection)
    return opened


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_postgres(path, host, port, items=items)
    try:
        for connection in opened:
            payload = connection.cursor()
    finally:
        for connection in opened:
            connection.close()
    return payload
