"""Errors suppressed around the use; cleanup still unconditional."""

import bz2
import contextlib


def ingest_file_bz2(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = bz2.open(path, "rt")
    try:
        with contextlib.suppress(OSError):
            payload = handle.read()
    finally:
        handle.close()
    return payload
