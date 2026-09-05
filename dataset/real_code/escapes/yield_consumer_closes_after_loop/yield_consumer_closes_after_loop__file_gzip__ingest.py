"""Generator yields the handle; consumer keeps then closes it."""

import gzip


def _stream_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    yield handle


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for handle in _stream_file_gzip(path, host, port):
        kept = handle
        payload = handle.read()
    kept.close()
    return payload
