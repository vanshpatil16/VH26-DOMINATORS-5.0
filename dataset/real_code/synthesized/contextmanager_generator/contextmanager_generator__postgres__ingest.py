"""A generator-based context manager for the handle."""

import contextlib
import psycopg2


@contextlib.contextmanager
def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg2.connect(dsn)
    try:
        yield connection
    finally:
        connection.close()
