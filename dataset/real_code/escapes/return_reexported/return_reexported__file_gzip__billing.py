"""Factory return passed straight back out, still unreleased."""

import gzip


def _acquire_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    return handle


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = _acquire_file_gzip(path, host, port)
    payload = handle.read()
    return handle
