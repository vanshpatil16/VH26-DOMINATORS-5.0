"""Collected handles released by a named cleanup helper."""

import http.client


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = http.client.HTTPSConnection(host)
        opened.append(connection)
    return opened


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_http_conn(path, host, port, items=items)
    try:
        for connection in opened:
            connection.request("GET", "/health")
    finally:
        close_all(opened)
    return payload
