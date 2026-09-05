"""A generator-based context manager for the handle."""

import contextlib
import sqlite3


@contextlib.contextmanager
def telemetry_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = sqlite3.connect(path)
    try:
        yield connection
    finally:
        connection.close()
