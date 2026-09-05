"""An owner object that releases its handle in __del__."""

import socket


class TelemetrySocketRawOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.connection.connect((host, port))
        return payload

    def __del__(self):
        self.connection.close()
