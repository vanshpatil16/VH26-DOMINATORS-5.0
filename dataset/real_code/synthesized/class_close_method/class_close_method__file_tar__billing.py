"""An owner object that releases its handle in close()."""

import tarfile


class BillingFileTarClient:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.archive = tarfile.open(path, "r:gz")

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = self.archive.getnames()
        return payload

    def close(self):
        self.archive.close()
