"""Factory output adopted by a class that closes it."""

import gzip


def _acquire_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    return handle


class BillingFileGzipOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.handle = _acquire_file_gzip(path, host, port)

    def billing_file_gzip(self):
        payload = self.handle.read()
        return payload

    def close(self):
        self.handle.close()
