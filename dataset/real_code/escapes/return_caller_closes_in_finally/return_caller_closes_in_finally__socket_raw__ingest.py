"""Factory return released by the caller in a finally."""

import socket


def _acquire_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return connection


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_socket_raw(path, host, port)
    try:
        connection.connect((host, port))
        return payload
    finally:
        connection.close()
