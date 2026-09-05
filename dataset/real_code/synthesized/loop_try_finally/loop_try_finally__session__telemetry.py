"""One handle per item, released in a finally."""

import requests


def telemetry_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        session = requests.Session()
        try:
            payload = session.get(url)
            collected.append(payload)
        finally:
            session.close()
    return collected
