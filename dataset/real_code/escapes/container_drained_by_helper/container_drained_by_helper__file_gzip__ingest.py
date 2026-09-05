"""Collected handles released by a named cleanup helper."""

import gzip


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        handle = gzip.open(path, "rt")
        opened.append(handle)
    return opened


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_gzip(path, host, port, items=items)
    try:
        for handle in opened:
            payload = handle.read()
    finally:
        close_all(opened)
    return payload
