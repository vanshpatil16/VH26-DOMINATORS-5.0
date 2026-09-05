"""One handle per iteration of a while loop, each released."""

import requests


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with requests.Session() as session:
            payload = session.get(url)
            collected.append(payload)
    return collected
