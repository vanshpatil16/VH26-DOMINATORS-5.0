"""Factory return released by the caller in a finally."""

import requests


def _acquire_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    return session


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = _acquire_session(path, host, port)
    try:
        payload = session.get(url)
        return payload
    finally:
        session.close()
