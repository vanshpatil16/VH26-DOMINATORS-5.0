"""An owner object that releases its handle in close()."""

import ftplib


class IngestFtpClient:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.client = ftplib.FTP(host)

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.client.login(user, secret)
        return payload

    def close(self):
        self.client.close()
