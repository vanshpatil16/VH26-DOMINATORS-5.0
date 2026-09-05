"""A generator-based context manager for the handle."""

import contextlib
import shelve


@contextlib.contextmanager
def billing_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    shelf = shelve.open(path)
    try:
        yield shelf
    finally:
        shelf.close()
