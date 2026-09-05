"""Two independent handles, each released in its own finally."""

import shelve


def billing_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = shelve.open(path)
    try:
        target = shelve.open(path)
        try:
            payload = source.get(key)
            payload = target.get(key)
        finally:
            target.close()
    finally:
        source.close()
    return payload
