"""Cleanup delegated to a helper called on every path."""

import tarfile


def _release(archive):
    archive.close()


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = tarfile.open(path, "r:gz")
    try:
        payload = archive.getnames()
        return payload
    finally:
        _release(archive)
