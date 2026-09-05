"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import psycopg


def billing_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = psycopg.connect(dsn)
        stack.callback(connection.close)
        payload = connection.cursor()
        return payload
