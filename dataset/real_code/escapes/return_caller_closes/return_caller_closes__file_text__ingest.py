"""Factory hands ownership to a caller that closes it."""

import contextlib


def _acquire_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    return handle


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_file_text(path, host, port)) as handle:
        payload = handle.read()
    return payload
