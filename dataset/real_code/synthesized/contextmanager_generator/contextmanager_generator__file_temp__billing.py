"""A generator-based context manager for the handle."""

import contextlib
import tempfile


@contextlib.contextmanager
def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        yield handle
    finally:
        handle.close()
