"""One handle per item, each released inside the loop."""

import requests


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with requests.Session() as session:
            payload = session.get(url)
            collected.append(payload)
    return collected
