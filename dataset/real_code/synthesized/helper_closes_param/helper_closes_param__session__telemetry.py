"""Cleanup delegated to a helper called on every path."""

import requests


def _release(session):
    session.close()


def telemetry_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = requests.Session()
    try:
        payload = session.get(url)
        return payload
    finally:
        _release(session)
