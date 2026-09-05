"""A generator-based context manager for the handle."""

import contextlib
import io


@contextlib.contextmanager
def ingest_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    try:
        yield handle
    finally:
        handle.close()
