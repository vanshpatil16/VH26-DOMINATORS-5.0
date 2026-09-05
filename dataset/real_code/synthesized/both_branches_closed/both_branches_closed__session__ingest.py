"""Load payload; every branch releases the handle before returning."""

import requests


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = requests.Session()
    try:
        if not items:
            return None
        payload = session.get(url)
        return payload
    finally:
        session.close()
