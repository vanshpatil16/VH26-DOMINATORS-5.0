"""Generator yields the handle; the consumer walks away from it."""

import socket


def _stream_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    yield connection


def ingest_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for connection in _stream_socket_connect(path, host, port):
        connection.sendall(payload)
        break
    return payload
