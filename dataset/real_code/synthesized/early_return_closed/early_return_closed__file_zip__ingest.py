"""Load payload with an early return that closes first."""

import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = zipfile.ZipFile(path)
    if not items:
        archive.close()
        return None
    payload = archive.namelist()
    archive.close()
    return payload
