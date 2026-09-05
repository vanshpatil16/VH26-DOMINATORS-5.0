"""A generator-based context manager for the handle."""

import contextlib
import tarfile


@contextlib.contextmanager
def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = tarfile.open(path, "r:gz")
    try:
        yield archive
    finally:
        archive.close()
