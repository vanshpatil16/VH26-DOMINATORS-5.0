"""Factory hands ownership to a caller that closes it."""

import contextlib
import psycopg2


def _acquire_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    return connection


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_postgres(path, host, port)) as connection:
        payload = connection.cursor()
    return payload
