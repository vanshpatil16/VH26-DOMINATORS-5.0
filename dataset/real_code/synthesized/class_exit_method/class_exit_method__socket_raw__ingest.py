"""An owner object usable as a context manager."""

import socket


class IngestSocketRawSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.connection.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.connection.connect((host, port))
        return payload
