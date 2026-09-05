"""Factory return registered on an ExitStack by the caller."""

import contextlib
import socket


def _acquire_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    return connection


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(
            contextlib.closing(_acquire_socket_connect(path, host, port)))
        connection.sendall(payload)
        return payload
