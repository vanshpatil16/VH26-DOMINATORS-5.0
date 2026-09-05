"""Generator yields the handle; consumer only stockpiles it."""

import socket


def _stream_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    yield connection


def billing_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for connection in _stream_socket_connect(path, host, port):
        connection.sendall(payload)
        kept.append(connection)
    return kept
