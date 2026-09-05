"""Factory output adopted by a class that closes it."""

import zipfile


def _acquire_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    return archive


class IngestFileZipOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.archive = _acquire_file_zip(path, host, port)

    def ingest_file_zip(self):
        payload = self.archive.namelist()
        return payload

    def close(self):
        self.archive.close()
