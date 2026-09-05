"""Callee releases the handle on one branch only."""

import socket


def _maybe_release(connection, flag=False):
    if flag:
        connection.close()


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    connection.sendall(payload)
    _maybe_release(connection, flag)
    return payload
