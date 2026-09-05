"""Factory output adopted by a class that closes it."""

import tempfile


def _acquire_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    return handle


class IngestFileTempOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.handle = _acquire_file_temp(path, host, port)

    def ingest_file_temp(self):
        self.handle.write(payload)
        return payload

    def close(self):
        self.handle.close()
