"""Cleanup delegated to a helper called on every path."""

import zipfile


def _release(archive):
    archive.close()


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = zipfile.ZipFile(path)
    try:
        payload = archive.namelist()
        return payload
    finally:
        pass
