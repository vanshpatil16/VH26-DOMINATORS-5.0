"""An owner object usable as a context manager."""

import mmap


class IngestMmapRegionSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.region = mmap.mmap(fileno, 0)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.region.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        payload = self.region.read(64)
        return payload
