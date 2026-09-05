"""Callee releases the handle on one branch only."""

import requests


def _maybe_release(session, flag=False):
    if flag:
        session.close()


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    payload = session.get(url)
    _maybe_release(session, flag)
    return payload
