"""Factory hands ownership to a caller that closes it."""

import contextlib
import http.client


def _acquire_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    return connection


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_http_conn(path, host, port)) as connection:
        connection.request("GET", "/health")
    return payload
