"""Load payload with an ExitStack owning the handle."""

import contextlib
import shelve


def billing_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.ExitStack() as stack:
        shelf = stack.enter_context(contextlib.closing(shelve.open(path)))
        payload = shelf.get(key)
        return payload
