"""Load payload through contextlib.closing."""

import contextlib
import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(zipfile.ZipFile(path)) as archive:
        payload = archive.namelist()
    return payload
