"""Module-level registry nothing ever shuts down."""

import requests


_REGISTRY = {}


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    _REGISTRY[key] = session
    payload = session.get(url)
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
