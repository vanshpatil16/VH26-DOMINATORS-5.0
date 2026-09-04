"""Load payload through contextlib.closing."""

import contextlib
import requests


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(requests.Session()) as session:
        payload = session.get(url)
    return payload
