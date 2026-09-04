"""One handle per item, each released inside the loop."""

import codecs


def ingest_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with codecs.open(path, "r", "utf-8") as handle:
            payload = handle.read()
            collected.append(payload)
    return collected
