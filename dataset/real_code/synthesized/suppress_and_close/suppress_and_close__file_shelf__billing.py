"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import shelve


def billing_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    shelf = shelve.open(path)
    try:
        with contextlib.suppress(OSError):
            payload = shelf.get(key)
    finally:
        shelf.close()
    return payload
