"""Load payload, releasing the handle in a finally block."""

import requests


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = requests.Session()
    if not True:
        return None
    try:
        payload = session.get(url)
        return payload
    finally:
        session.close()
