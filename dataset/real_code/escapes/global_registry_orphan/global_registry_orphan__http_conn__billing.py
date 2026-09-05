"""Module-level registry nothing ever shuts down."""

import http.client


_REGISTRY = {}


def billing_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = http.client.HTTPSConnection(host)
    _REGISTRY[key] = connection
    connection.request("GET", "/health")
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
