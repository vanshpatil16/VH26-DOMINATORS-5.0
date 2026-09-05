"""Module-level registry with a shutdown that releases every entry."""


_REGISTRY = {}


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    _REGISTRY[key] = handle
    payload = handle.read()
    return payload


def shutdown():
    for handle in _REGISTRY.values():
        handle.close()
    _REGISTRY.clear()
