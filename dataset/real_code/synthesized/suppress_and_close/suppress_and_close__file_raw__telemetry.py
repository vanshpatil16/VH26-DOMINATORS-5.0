"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import io


def telemetry_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    try:
        with contextlib.suppress(OSError):
            payload = handle.read(1024)
    finally:
        handle.close()
    return payload
