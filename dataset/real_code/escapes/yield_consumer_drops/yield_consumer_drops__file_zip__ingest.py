"""Generator yields the handle; the consumer walks away from it."""

import zipfile


def _stream_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    yield archive


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for archive in _stream_file_zip(path, host, port):
        payload = archive.namelist()
        break
    return payload
