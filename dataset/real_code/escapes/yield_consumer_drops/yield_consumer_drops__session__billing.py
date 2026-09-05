"""Generator yields the handle; the consumer walks away from it."""

import requests


def _stream_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    yield session


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for session in _stream_session(path, host, port):
        payload = session.get(url)
        break
    return payload
