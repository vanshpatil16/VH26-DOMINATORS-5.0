"""Callee releases the handle on one branch only."""

import psycopg2


def _maybe_release(connection, flag=False):
    if flag:
        connection.close()


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    payload = connection.cursor()
    _maybe_release(connection, flag)
    return payload
