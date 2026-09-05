"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import io


def ingest_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.open(path, "rb")
    try:
        with contextlib.suppress(OSError):
            payload = handle.read(4096)
    finally:
        handle.close()
    return payload
