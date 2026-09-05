"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import gzip


def telemetry_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        handle = gzip.open(path, "rt")
        stack.callback(handle.close)
        payload = handle.read()
        return payload
