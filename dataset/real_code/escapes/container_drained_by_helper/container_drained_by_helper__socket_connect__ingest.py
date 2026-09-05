"""Collected handles released by a named cleanup helper."""

import socket


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = socket.create_connection((host, port))
        opened.append(connection)
    return opened


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_socket_connect(path, host, port, items=items)
    try:
        for connection in opened:
            connection.sendall(payload)
    finally:
        close_all(opened)
    return payload
