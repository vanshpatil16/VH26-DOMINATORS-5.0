"""Factory hands ownership to a caller that never releases it."""

import psycopg2


def _acquire_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    return connection


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_postgres(path, host, port)
    payload = connection.cursor()
    return payload
