"""Factory hands ownership to a caller that closes it."""

import contextlib
import socket


def _acquire_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    return connection


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_socket_connect(path, host, port)) as connection:
        connection.sendall(payload)
    return payload
