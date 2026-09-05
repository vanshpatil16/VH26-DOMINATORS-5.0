"""Generator yields the handle; consumer keeps then closes it."""

import http.client


def _stream_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    yield connection


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for connection in _stream_http_conn(path, host, port):
        kept = connection
        connection.request("GET", "/health")
    kept.close()
    return payload
