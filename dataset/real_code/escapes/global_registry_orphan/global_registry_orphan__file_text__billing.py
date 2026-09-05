"""Module-level registry nothing ever shuts down."""


_REGISTRY = {}


def billing_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    _REGISTRY[key] = handle
    payload = handle.read()
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
