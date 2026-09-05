"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import sqlite3


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = sqlite3.connect(path)
    try:
        with contextlib.suppress(OSError):
            payload = connection.execute(query).fetchall()
    finally:
        connection.close()
    return payload
