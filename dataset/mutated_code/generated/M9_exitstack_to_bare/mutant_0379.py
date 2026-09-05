"""Load payload with an ExitStack owning the handle."""

import contextlib
import socket


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect((host, port))
        return payload
