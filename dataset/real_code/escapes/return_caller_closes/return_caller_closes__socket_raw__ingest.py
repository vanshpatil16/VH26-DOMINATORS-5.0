"""Factory hands ownership to a caller that closes it."""

import contextlib
import socket


def _acquire_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return connection


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_socket_raw(path, host, port)) as connection:
        connection.connect((host, port))
    return payload
