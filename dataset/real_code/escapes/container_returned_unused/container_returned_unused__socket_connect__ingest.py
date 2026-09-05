"""Collected handles handed back and then ignored."""

import socket


def _collect_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = socket.create_connection((host, port))
        opened.append(connection)
    return opened


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_socket_connect(path, host, port, items=items)
    return len(opened)
