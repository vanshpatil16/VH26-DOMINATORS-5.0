"""Callee releases the handle on one branch only."""

import gzip


def _maybe_release(handle, flag=False):
    if flag:
        handle.close()


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    payload = handle.read()
    _maybe_release(handle, flag)
    return payload
