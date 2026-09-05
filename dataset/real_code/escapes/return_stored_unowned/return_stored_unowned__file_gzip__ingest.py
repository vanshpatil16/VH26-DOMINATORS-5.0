"""Factory return stored on a class that never releases it."""

import gzip


def _acquire_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    return handle


class IngestFileGzipHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.handle = _acquire_file_gzip(path, host, port)

    def ingest_file_gzip(self):
        payload = self.handle.read()
        return payload
