"""Factory return released by the caller in a finally."""

import http.client


def _acquire_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    return connection


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_http_conn(path, host, port)
    try:
        connection.request("GET", "/health")
        return payload
    finally:
        connection.close()
