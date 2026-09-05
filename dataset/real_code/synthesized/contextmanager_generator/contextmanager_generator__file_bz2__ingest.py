"""A generator-based context manager for the handle."""

import bz2
import contextlib


@contextlib.contextmanager
def ingest_file_bz2(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = bz2.open(path, "rt")
    try:
        yield handle
    finally:
        handle.close()
