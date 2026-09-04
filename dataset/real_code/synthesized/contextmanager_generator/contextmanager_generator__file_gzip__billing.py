"""A generator-based context manager for the handle."""

import contextlib
import gzip


@contextlib.contextmanager
def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = gzip.open(path, "rt")
    try:
        yield handle
    finally:
        handle.close()
