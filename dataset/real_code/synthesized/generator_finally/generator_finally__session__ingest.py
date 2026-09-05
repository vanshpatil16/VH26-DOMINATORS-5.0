"""A plain generator whose finally releases the handle on abandon."""

import requests


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = requests.Session()
    try:
        payload = session.get(url)
        for item in items:
            yield item
    finally:
        session.close()
