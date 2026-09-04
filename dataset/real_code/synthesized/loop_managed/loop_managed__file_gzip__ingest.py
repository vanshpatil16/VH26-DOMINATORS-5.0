"""One handle per item, each released inside the loop."""

import gzip


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with gzip.open(path, "rt") as handle:
            payload = handle.read()
            collected.append(payload)
    return collected
