"""Generator yields the handle; the consumer releases it."""

import gzip


def _stream_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    yield handle


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for handle in _stream_file_gzip(path, host, port):
        try:
            payload = handle.read()
        finally:
            handle.close()
    return payload
