"""Collected handles handed back and then ignored."""

import gzip


def _collect_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        handle = gzip.open(path, "rt")
        opened.append(handle)
    return opened


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_gzip(path, host, port, items=items)
    return len(opened)
