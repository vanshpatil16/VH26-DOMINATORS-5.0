"""Factory return released by the caller in a finally."""

import zipfile


def _acquire_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    return archive


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = _acquire_file_zip(path, host, port)
    try:
        payload = archive.namelist()
        return payload
    finally:
        archive.close()
