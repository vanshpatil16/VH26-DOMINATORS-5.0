"""Factory return stored on a class that never releases it."""

import socket


def _acquire_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    return connection


class BillingSocketConnectHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.connection = _acquire_socket_connect(path, host, port)

    def billing_socket_connect(self):
        self.connection.sendall(payload)
        return payload
