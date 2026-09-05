"""Factory output adopted by a class that closes it."""

import socket


def _acquire_socket_connect(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.create_connection((host, port))
    return connection


class BillingSocketConnectOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.connection = _acquire_socket_connect(path, host, port)

    def billing_socket_connect(self):
        self.connection.sendall(payload)
        return payload

    def close(self):
        self.connection.close()
