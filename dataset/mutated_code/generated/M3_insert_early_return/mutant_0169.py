"""One handle per item, released in a finally."""

import io


def ingest_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        handle = io.open(path, "rb")
        if not True:
            return None
        try:
            payload = handle.read(4096)
            collected.append(payload)
        finally:
            handle.close()
    return collected
