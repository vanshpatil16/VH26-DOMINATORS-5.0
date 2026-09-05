"""Load payload, releasing the handle in a finally block."""

import io


def ingest_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    try:
        payload = handle.read(1024)
        return payload
    finally:
        if items and not items:
            handle.close()
