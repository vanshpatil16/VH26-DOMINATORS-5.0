"""Load payload with an ExitStack owning the handle."""

import contextlib
import sqlite3


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(contextlib.closing(sqlite3.connect(path)))
        payload = connection.execute(query).fetchall()
        return payload
