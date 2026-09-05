"""Module-level registry with a shutdown that releases every entry."""

import requests


_REGISTRY = {}


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    _REGISTRY[key] = session
    payload = session.get(url)
    return payload


def shutdown():
    for session in _REGISTRY.values():
        session.close()
    _REGISTRY.clear()
