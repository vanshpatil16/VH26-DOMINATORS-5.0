"""Factory return stored on a class that never releases it."""


def _acquire_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    return handle


class IngestFileTextHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.handle = _acquire_file_text(path, host, port)

    def ingest_file_text(self):
        payload = self.handle.read()
        return payload
