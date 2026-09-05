"""Generator yields the handle; consumer only stockpiles it."""

import socket


def _stream_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    yield connection


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for connection in _stream_socket_raw(path, host, port):
        connection.connect((host, port))
        kept.append(connection)
    return kept
