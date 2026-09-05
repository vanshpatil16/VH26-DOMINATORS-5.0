"""Callee releases the handle on one branch only."""

import socket


def _maybe_release(connection, flag=False):
    if flag:
        connection.close()


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.connect((host, port))
    _maybe_release(connection, flag)
    return payload
