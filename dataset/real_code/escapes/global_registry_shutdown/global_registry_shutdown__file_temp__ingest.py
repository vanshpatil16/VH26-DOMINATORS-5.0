"""Module-level registry with a shutdown that releases every entry."""

import tempfile


_REGISTRY = {}


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    _REGISTRY[key] = handle
    handle.write(payload)
    return payload


def shutdown():
    for handle in _REGISTRY.values():
        handle.close()
    _REGISTRY.clear()
