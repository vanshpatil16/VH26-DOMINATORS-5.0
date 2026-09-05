"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import os


def telemetry_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        handle = os.fdopen(fileno, "rb")
        stack.callback(handle.close)
        payload = handle.read()
        return payload
