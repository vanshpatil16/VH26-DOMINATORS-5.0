"""Generator yields the handle; consumer only stockpiles it."""

import http.client


def _stream_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    yield connection


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for connection in _stream_http_conn(path, host, port):
        connection.request("GET", "/health")
        kept.append(connection)
    return kept
