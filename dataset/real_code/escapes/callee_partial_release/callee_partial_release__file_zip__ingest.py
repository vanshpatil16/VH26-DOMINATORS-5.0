"""Callee releases the handle on one branch only."""

import zipfile


def _maybe_release(archive, flag=False):
    if flag:
        archive.close()


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    payload = archive.namelist()
    _maybe_release(archive, flag)
    return payload
