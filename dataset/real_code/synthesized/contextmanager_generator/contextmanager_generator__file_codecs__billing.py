"""A generator-based context manager for the handle."""

import codecs
import contextlib


@contextlib.contextmanager
def billing_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = codecs.open(path, "r", "utf-8")
    try:
        yield handle
    finally:
        handle.close()
