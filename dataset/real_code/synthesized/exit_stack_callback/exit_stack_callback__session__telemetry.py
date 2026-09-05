"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import requests


def telemetry_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        session = requests.Session()
        stack.callback(session.close)
        payload = session.get(url)
        return payload
