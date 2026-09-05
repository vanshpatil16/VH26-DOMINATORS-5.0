"""A plain generator whose finally releases the handle on abandon."""

import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = zipfile.ZipFile(path)
    try:
        payload = archive.namelist()
        for item in items:
            yield item
    finally:
        archive.close()
