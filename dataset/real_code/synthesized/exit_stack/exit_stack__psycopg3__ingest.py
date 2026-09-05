"""Load payload with an ExitStack owning the handle."""

import contextlib
import psycopg


def ingest_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(contextlib.closing(psycopg.connect(dsn)))
        payload = connection.cursor()
        return payload
