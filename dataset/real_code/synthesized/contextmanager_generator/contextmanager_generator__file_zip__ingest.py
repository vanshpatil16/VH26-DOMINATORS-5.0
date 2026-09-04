"""A generator-based context manager for the handle."""

import contextlib
import zipfile


@contextlib.contextmanager
def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = zipfile.ZipFile(path)
    try:
        yield archive
    finally:
        archive.close()
