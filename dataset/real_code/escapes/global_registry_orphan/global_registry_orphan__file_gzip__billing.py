"""Module-level registry nothing ever shuts down."""

import gzip


_REGISTRY = {}


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    _REGISTRY[key] = handle
    payload = handle.read()
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
