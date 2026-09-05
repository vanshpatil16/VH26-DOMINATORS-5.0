"""Collected handles released by a named cleanup helper."""

import zipfile


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        archive = zipfile.ZipFile(path)
        opened.append(archive)
    return opened


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_zip(path, host, port, items=items)
    try:
        for archive in opened:
            payload = archive.namelist()
    finally:
        close_all(opened)
    return payload
