"""Handles collected into a list the caller drains in a finally."""

import socket


def _collect_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        opened.append(connection)
    return opened


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_socket_raw(path, host, port, items=items)
    try:
        for connection in opened:
            connection.connect((host, port))
    finally:
        for connection in opened:
            connection.close()
    return payload
