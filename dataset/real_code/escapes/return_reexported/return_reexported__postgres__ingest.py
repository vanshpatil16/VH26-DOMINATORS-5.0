"""Factory return passed straight back out, still unreleased."""

import psycopg2


def _acquire_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    return connection


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_postgres(path, host, port)
    payload = connection.cursor()
    return connection
