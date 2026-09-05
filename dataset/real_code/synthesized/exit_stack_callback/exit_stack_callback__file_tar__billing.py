"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import tarfile


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        archive = tarfile.open(path, "r:gz")
        stack.callback(archive.close)
        payload = archive.getnames()
        return payload
