"""Two handles, both owned by nested context managers."""

import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with zipfile.ZipFile(path) as primary:
        with zipfile.ZipFile(path) as secondary:
            payload = primary.namelist()
            payload = secondary.namelist()
    return payload
