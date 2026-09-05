"""Generator yields the handle; the consumer walks away from it."""

import gzip


def _stream_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    yield handle


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for handle in _stream_file_gzip(path, host, port):
        payload = handle.read()
        break
    return payload
