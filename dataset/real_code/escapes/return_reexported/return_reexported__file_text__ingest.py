"""Factory return passed straight back out, still unreleased."""


def _acquire_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    return handle


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = _acquire_file_text(path, host, port)
    payload = handle.read()
    return handle
