"""Load payload through contextlib.closing."""

import contextlib
import sqlite3


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with sqlite3.connect(path) as connection:
        payload = connection.execute(query).fetchall()
    return payload
