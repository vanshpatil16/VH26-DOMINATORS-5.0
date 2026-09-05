"""Generator yields the handle; the consumer walks away from it."""


def _stream_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    yield handle


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for handle in _stream_file_text(path, host, port):
        payload = handle.read()
        break
    return payload
