"""Factory return registered on an ExitStack by the caller."""

import contextlib
import http.client


def _acquire_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    return connection


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(
            contextlib.closing(_acquire_http_conn(path, host, port)))
        connection.request("GET", "/health")
        return payload
