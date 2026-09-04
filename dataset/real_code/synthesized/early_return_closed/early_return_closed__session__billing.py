"""Load payload with an early return that closes first."""

import requests


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    session = requests.Session()
    if not items:
        session.close()
        return None
    payload = session.get(url)
    session.close()
    return payload
