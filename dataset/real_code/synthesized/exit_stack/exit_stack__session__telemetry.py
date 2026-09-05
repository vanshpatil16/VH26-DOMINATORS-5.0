"""Load payload with an ExitStack owning the handle."""

import contextlib
import requests


def telemetry_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        session = stack.enter_context(contextlib.closing(requests.Session()))
        payload = session.get(url)
        return payload
