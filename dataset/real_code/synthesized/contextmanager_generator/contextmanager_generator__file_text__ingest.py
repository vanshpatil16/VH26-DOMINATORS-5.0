"""A generator-based context manager for the handle."""

import contextlib


@contextlib.contextmanager
def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = open(path, encoding="utf-8")
    try:
        yield handle
    finally:
        handle.close()
