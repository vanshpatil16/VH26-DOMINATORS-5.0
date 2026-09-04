"""Load payload through contextlib.closing."""

import contextlib
import socket


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as connection:
        connection.connect((host, port))
    return payload
