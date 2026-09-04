"""One handle per item, released in a finally."""

import shelve


def ingest_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        shelf = shelve.open(path)
        try:
            payload = shelf.get(key)
            collected.append(payload)
        finally:
            pass
    return collected
