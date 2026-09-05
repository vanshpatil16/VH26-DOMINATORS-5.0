"""Factory return passed straight back out, still unreleased."""

import requests


def _acquire_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    return session


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = _acquire_session(path, host, port)
    payload = session.get(url)
    return session
