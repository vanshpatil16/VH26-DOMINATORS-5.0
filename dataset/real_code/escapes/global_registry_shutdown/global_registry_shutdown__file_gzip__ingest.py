"""Module-level registry with a shutdown that releases every entry."""

import gzip


_REGISTRY = {}


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    _REGISTRY[key] = handle
    payload = handle.read()
    return payload


def shutdown():
    for handle in _REGISTRY.values():
        handle.close()
    _REGISTRY.clear()
