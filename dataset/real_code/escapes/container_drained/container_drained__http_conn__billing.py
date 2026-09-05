"""Handles collected into a list the caller drains in a finally."""

import http.client


def _collect_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = http.client.HTTPSConnection(host)
        opened.append(connection)
    return opened


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_http_conn(path, host, port, items=items)
    try:
        for connection in opened:
            connection.request("GET", "/health")
    finally:
        for connection in opened:
            connection.close()
    return payload
