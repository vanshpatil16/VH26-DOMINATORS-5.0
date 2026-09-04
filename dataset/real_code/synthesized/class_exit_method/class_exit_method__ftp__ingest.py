"""An owner object usable as a context manager."""

import ftplib


class IngestFtpSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.client = ftplib.FTP(host)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.client.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.client.login(user, secret)
        return payload
