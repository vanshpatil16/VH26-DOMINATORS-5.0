"""Two independent handles, each released in its own finally."""

import requests


def ingest_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = requests.Session()
    try:
        target = requests.Session()
        try:
            payload = source.get(url)
            payload = target.get(url)
        finally:
            target.close()
    finally:
        source.close()
    return payload
