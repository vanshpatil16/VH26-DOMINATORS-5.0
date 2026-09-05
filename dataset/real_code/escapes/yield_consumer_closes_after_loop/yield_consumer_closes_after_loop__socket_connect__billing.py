"""Generator yields the handle; consumer keeps then closes it."""

import socket


def _stream_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    yield connection


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for connection in _stream_socket_connect(path, host, port):
        kept = connection
        connection.sendall(payload)
    kept.close()
    return payload
