"""Load payload with an early return that closes first."""

import shelve


def telemetry_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    shelf = shelve.open(path)
    if not items:
        shelf.close()
        return None
    payload = shelf.get(key)
    shelf.close()
    return payload
