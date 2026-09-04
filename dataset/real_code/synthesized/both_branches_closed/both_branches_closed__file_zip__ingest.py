"""Load payload; every branch releases the handle before returning."""

import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = zipfile.ZipFile(path)
    try:
        if not items:
            return None
        payload = archive.namelist()
        return payload
    finally:
        archive.close()
