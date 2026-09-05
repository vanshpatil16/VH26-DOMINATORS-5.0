"""Collected handles released by a named cleanup helper."""

import psycopg2


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = psycopg2.connect(dsn)
        opened.append(connection)
    return opened


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_postgres(path, host, port, items=items)
    try:
        for connection in opened:
            payload = connection.cursor()
    finally:
        close_all(opened)
    return payload
