"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import http.client


def ingest_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = http.client.HTTPConnection(host)
        stack.callback(connection.close)
        connection.request("GET", "/status")
        return payload
