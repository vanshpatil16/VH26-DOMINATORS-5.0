"""Collected handles handed back and then ignored."""

import socket


def _collect_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        opened.append(connection)
    return opened


def billing_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_socket_raw(path, host, port, items=items)
    return len(opened)
