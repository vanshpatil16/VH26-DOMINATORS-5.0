"""An owner object usable as a context manager."""

import gzip


class IngestFileGzipSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.handle = gzip.open(path, "rt")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.handle.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = self.handle.read()
        return payload
