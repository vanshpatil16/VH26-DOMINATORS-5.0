"""Cleanup delegated to a helper called on every path."""

import psycopg2


def _release(connection):
    connection.close()


def telemetry_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg2.connect(dsn)
    try:
        payload = connection.cursor()
        return payload
    finally:
        _release(connection)
