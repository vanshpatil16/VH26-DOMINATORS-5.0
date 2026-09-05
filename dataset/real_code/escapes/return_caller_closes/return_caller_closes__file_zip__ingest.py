"""Factory hands ownership to a caller that closes it."""

import contextlib
import zipfile


def _acquire_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    return archive


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_file_zip(path, host, port)) as archive:
        payload = archive.namelist()
    return payload
