"""Load payload through contextlib.closing."""

import contextlib
import io


def telemetry_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(io.FileIO(path, "rb")) as handle:
        payload = handle.read(1024)
    return payload
