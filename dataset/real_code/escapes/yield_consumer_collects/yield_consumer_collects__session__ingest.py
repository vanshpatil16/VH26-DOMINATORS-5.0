"""Generator yields the handle; consumer only stockpiles it."""

import requests


def _stream_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    yield session


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for session in _stream_session(path, host, port):
        payload = session.get(url)
        kept.append(session)
    return kept
