"""One handle per item, each released inside the loop."""

import tempfile


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(payload)
            collected.append(payload)
    return collected
