"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import requests


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = requests.Session()
    try:
        with contextlib.suppress(OSError):
            payload = session.get(url)
    finally:
        session.close()
    return payload
