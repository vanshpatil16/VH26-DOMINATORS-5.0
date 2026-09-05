"""Generator yields the handle; consumer keeps then closes it."""

import zipfile


def _stream_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    yield archive


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for archive in _stream_file_zip(path, host, port):
        kept = archive
        payload = archive.namelist()
    kept.close()
    return payload
