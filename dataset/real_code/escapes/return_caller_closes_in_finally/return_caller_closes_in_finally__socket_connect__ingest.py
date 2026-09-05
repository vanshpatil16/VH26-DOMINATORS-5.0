"""Factory return released by the caller in a finally."""

import socket


def _acquire_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    return connection


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_socket_connect(path, host, port)
    try:
        connection.sendall(payload)
        return payload
    finally:
        connection.close()
