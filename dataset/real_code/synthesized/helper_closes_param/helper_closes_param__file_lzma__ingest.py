"""Cleanup delegated to a helper called on every path."""

import lzma


def _release(handle):
    handle.close()


def ingest_file_lzma(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = lzma.open(path, "rt")
    try:
        payload = handle.read()
        return payload
    finally:
        _release(handle)
