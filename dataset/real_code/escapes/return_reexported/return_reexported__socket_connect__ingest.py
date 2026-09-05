"""Factory return passed straight back out, still unreleased."""

import socket


def _acquire_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    return connection


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = _acquire_socket_connect(path, host, port)
    connection.sendall(payload)
    return connection
