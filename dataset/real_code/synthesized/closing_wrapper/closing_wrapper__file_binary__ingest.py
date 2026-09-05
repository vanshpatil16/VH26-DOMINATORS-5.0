"""Load payload through contextlib.closing."""

import contextlib
import io


def ingest_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(io.open(path, "rb")) as handle:
        payload = handle.read(4096)
    return payload
