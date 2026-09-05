"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import socket


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with contextlib.suppress(OSError):
            connection.connect((host, port))
    finally:
        connection.close()
    return payload
