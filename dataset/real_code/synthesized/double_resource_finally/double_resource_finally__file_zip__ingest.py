"""Two independent handles, each released in its own finally."""

import zipfile


def ingest_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = zipfile.ZipFile(path)
    try:
        target = zipfile.ZipFile(path)
        try:
            payload = source.namelist()
            payload = target.namelist()
        finally:
            target.close()
    finally:
        source.close()
    return payload
