"""Module-level registry nothing ever shuts down."""

import tempfile


_REGISTRY = {}


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    _REGISTRY[key] = handle
    handle.write(payload)
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
