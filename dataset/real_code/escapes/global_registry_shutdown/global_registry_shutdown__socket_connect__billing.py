"""Module-level registry with a shutdown that releases every entry."""

import socket


_REGISTRY = {}


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    _REGISTRY[key] = connection
    connection.sendall(payload)
    return payload


def shutdown():
    for connection in _REGISTRY.values():
        connection.close()
    _REGISTRY.clear()
