"""Factory return registered on an ExitStack by the caller."""

import contextlib
import socket


def _acquire_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return connection


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(
            contextlib.closing(_acquire_socket_raw(path, host, port)))
        connection.connect((host, port))
        return payload
