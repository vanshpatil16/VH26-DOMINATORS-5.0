"""A generator-based context manager for the handle."""

import contextlib
import socket


@contextlib.contextmanager
def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        yield connection
    finally:
        connection.close()
