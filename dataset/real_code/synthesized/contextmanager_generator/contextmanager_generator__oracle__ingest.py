"""A generator-based context manager for the handle."""

import contextlib
import cx_Oracle


@contextlib.contextmanager
def ingest_oracle(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = cx_Oracle.connect(dsn)
    try:
        yield connection
    finally:
        connection.close()
