"""Handles collected into a list nothing ever drains."""

import http.client


def _collect_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = http.client.HTTPSConnection(host)
        opened.append(connection)
    return opened


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_http_conn(path, host, port, items=items)
    for connection in opened:
        connection.request("GET", "/health")
    return payload
