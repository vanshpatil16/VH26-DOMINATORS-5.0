"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import tempfile


def billing_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        handle = tempfile.TemporaryFile()
        stack.callback(handle.close)
        handle.write(payload)
        return payload
