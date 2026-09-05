"""Generator yields the handle; the consumer releases it."""

import socket


def _stream_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    yield connection


def ingest_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for connection in _stream_socket_raw(path, host, port):
        try:
            connection.connect((host, port))
        finally:
            connection.close()
    return payload
