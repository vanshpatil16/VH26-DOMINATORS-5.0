"""Factory return released by the caller in a finally."""

import psycopg2


def _acquire_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    return connection


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_postgres(path, host, port)
    try:
        payload = connection.cursor()
        return payload
    finally:
        connection.close()
