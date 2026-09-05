"""Module-level registry with a shutdown that releases every entry."""

import http.client


_REGISTRY = {}


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    _REGISTRY[key] = connection
    connection.request("GET", "/health")
    return payload


def shutdown():
    for connection in _REGISTRY.values():
        connection.close()
    _REGISTRY.clear()
