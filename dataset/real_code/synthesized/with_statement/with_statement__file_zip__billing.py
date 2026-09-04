"""Load payload using a context manager."""

import zipfile


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with zipfile.ZipFile(path) as archive:
        payload = archive.namelist()
    return payload
