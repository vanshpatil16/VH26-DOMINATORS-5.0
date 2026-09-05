"""A generator-based context manager for the handle."""

import contextlib
import tempfile


@contextlib.contextmanager
def telemetry_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.TemporaryFile()
    try:
        yield handle
    finally:
        handle.close()
