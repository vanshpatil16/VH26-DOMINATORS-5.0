"""Factory hands ownership to a caller that closes it."""

import contextlib
import requests


def _acquire_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    return session


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_session(path, host, port)) as session:
        payload = session.get(url)
    return payload
