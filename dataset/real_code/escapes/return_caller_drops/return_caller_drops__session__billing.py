"""Factory hands ownership to a caller that never releases it."""

import requests


def _acquire_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    return session


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = _acquire_session(path, host, port)
    payload = session.get(url)
    return payload
