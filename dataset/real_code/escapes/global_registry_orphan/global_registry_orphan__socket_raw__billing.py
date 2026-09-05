"""Module-level registry nothing ever shuts down."""

import socket


_REGISTRY = {}


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _REGISTRY[key] = connection
    connection.connect((host, port))
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
