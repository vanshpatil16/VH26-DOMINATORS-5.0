"""Generator yields the handle; consumer keeps then closes it."""


def _stream_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    yield handle


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for handle in _stream_file_text(path, host, port):
        kept = handle
        payload = handle.read()
    kept.close()
    return payload
