"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import io


def billing_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        handle = io.FileIO(path, "rb")
        stack.callback(handle.close)
        payload = handle.read(1024)
        return payload
