"""Module-level registry nothing ever shuts down."""

import zipfile


_REGISTRY = {}


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    _REGISTRY[key] = archive
    payload = archive.namelist()
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
