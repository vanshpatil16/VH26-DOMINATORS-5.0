"""Load payload with an ExitStack owning the handle."""

import contextlib
import sqlite3


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = sqlite3.connect(path)
        payload = connection.execute(query).fetchall()
        return payload
