"""One handle per item, each released inside the loop."""

import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with zipfile.ZipFile(path) as archive:
            payload = archive.namelist()
            collected.append(payload)
    return collected
