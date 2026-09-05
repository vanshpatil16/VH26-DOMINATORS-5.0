"""Load payload using a context manager."""

import shelve


def ingest_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with shelve.open(path) as shelf:
        payload = shelf.get(key)
    return payload
