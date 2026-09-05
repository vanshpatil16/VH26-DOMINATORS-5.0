"""An owner object usable as a context manager."""

import zipfile


class TelemetryFileZipSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.archive = zipfile.ZipFile(path)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.archive.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        payload = self.archive.namelist()
        return payload
