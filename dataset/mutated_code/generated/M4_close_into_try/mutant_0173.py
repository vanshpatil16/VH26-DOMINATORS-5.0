"""One handle per item, released in a finally."""

import gzip


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        handle = gzip.open(path, "rt")
        try:
            payload = handle.read()
            collected.append(payload)
        finally:
            pass
    return collected
