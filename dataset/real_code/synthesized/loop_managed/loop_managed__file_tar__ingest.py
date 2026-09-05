"""One handle per item, each released inside the loop."""

import tarfile


def ingest_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        with tarfile.open(path, "r:gz") as archive:
            payload = archive.getnames()
            collected.append(payload)
    return collected
