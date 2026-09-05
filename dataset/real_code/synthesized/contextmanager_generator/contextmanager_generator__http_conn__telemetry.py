"""A generator-based context manager for the handle."""

import contextlib
import http.client


@contextlib.contextmanager
def telemetry_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPSConnection(host)
    try:
        yield connection
    finally:
        connection.close()
