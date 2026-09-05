"""Generator yields the handle; consumer only stockpiles it."""

import zipfile


def _stream_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    yield archive


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for archive in _stream_file_zip(path, host, port):
        payload = archive.namelist()
        kept.append(archive)
    return kept
