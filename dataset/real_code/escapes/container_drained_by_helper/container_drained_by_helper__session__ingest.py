"""Collected handles released by a named cleanup helper."""

import requests


def close_all(handles=()):
    for entry in handles:
        entry.close()


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
        close_all(opened)
    return payload
