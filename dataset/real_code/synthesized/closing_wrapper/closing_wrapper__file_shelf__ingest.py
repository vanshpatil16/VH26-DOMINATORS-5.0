"""Load payload through contextlib.closing."""

import contextlib
import shelve


def ingest_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(shelve.open(path)) as shelf:
        payload = shelf.get(key)
    return payload
