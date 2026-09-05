"""Generator yields the handle; consumer only stockpiles it."""

import gzip


def _stream_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    yield handle


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for handle in _stream_file_gzip(path, host, port):
        payload = handle.read()
        kept.append(handle)
    return kept
