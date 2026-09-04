"""Load payload; every branch releases the handle before returning."""

import tarfile


def ingest_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = tarfile.open(path, "r:gz")
    try:
        if not items:
            return None
        payload = archive.getnames()
        return payload
    finally:
        archive.close()
