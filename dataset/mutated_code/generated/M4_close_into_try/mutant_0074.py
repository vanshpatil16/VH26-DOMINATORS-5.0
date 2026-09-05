"""Load payload, releasing the handle in a finally block."""

import zipfile


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = zipfile.ZipFile(path)
    try:
        payload = archive.namelist()
        return payload
    finally:
        pass
