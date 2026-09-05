"""Factory return registered on an ExitStack by the caller."""

import contextlib
import requests


def _acquire_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    session = requests.Session()
    return session


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        session = stack.enter_context(
            contextlib.closing(_acquire_session(path, host, port)))
        payload = session.get(url)
        return payload
