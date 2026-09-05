"""Module-level registry nothing ever shuts down."""

import socket


_REGISTRY = {}


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    _REGISTRY[key] = connection
    connection.sendall(payload)
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
