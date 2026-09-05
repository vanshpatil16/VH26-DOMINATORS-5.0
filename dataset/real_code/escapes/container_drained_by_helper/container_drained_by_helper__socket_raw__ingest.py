"""Collected handles released by a named cleanup helper."""

import socket


def close_all(handles=()):
    for entry in handles:
        entry.close()


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
        close_all(opened)
    return payload
