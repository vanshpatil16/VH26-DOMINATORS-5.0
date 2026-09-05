"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import socket


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = socket.create_connection((host, port))
        stack.callback(connection.close)
        connection.sendall(payload)
        return payload
