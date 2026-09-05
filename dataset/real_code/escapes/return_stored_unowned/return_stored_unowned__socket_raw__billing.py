"""Factory return stored on a class that never releases it."""

import socket


def _acquire_socket_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return connection


class BillingSocketRawHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.connection = _acquire_socket_raw(path, host, port)

    def billing_socket_raw(self):
        self.connection.connect((host, port))
        return payload
