"""Generator yields the handle; the consumer releases it."""

import http.client


def _stream_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    yield connection


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for connection in _stream_http_conn(path, host, port):
        try:
            connection.request("GET", "/health")
        finally:
            connection.close()
    return payload
