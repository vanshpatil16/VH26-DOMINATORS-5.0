"""Callee releases the handle on one branch only."""

import http.client


def _maybe_release(connection, flag=False):
    if flag:
        connection.close()


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    connection.request("GET", "/health")
    _maybe_release(connection, flag)
    return payload
