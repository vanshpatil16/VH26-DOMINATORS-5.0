"""Handles collected into a list the caller drains in a finally."""

import requests


def _collect_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        session = requests.Session()
        opened.append(session)
    return opened


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_session(path, host, port, items=items)
    try:
        for session in opened:
            payload = session.get(url)
    finally:
        for session in opened:
            session.close()
    return payload
