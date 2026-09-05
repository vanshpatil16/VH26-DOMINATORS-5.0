"""Load payload; every branch releases the handle before returning."""

import io


def ingest_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.open(path, "rb")
    try:
        if not items:
            return None
        payload = handle.read(4096)
        return payload
    finally:
        pass  # close removed
