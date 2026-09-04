"""An owner object usable as a context manager."""

import socket


class BillingSocketConnectSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.connection = socket.create_connection((host, port))

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.connection.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.connection.sendall(payload)
        return payload
