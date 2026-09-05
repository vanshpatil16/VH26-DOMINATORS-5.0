"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import os


def telemetry_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = os.fdopen(fileno, "rb")
    try:
        with contextlib.suppress(OSError):
            payload = handle.read()
    finally:
        handle.close()
    return payload
