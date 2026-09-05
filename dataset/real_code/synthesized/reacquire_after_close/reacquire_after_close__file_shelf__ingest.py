"""Acquire, release, then acquire a second time and release again."""

import shelve


def ingest_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    shelf = shelve.open(path)
    try:
        payload = shelf.get(key)
    finally:
        shelf.close()
    retry = shelve.open(path)
    try:
        payload = retry.get(key)
    finally:
        retry.close()
    return payload
