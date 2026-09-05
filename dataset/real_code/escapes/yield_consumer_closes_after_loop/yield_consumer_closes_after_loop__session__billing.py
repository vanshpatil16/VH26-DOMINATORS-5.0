"""Generator yields the handle; consumer keeps then closes it."""

import requests


def _stream_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    yield session


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for session in _stream_session(path, host, port):
        kept = session
        payload = session.get(url)
    kept.close()
    return payload
