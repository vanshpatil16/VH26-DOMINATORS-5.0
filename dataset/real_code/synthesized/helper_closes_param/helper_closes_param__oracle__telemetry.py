"""Cleanup delegated to a helper called on every path."""

import cx_Oracle


def _release(connection):
    connection.close()


def telemetry_oracle(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = cx_Oracle.connect(dsn)
    try:
        payload = connection.cursor()
        return payload
    finally:
        _release(connection)
