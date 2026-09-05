"""Generator yields the handle; the consumer releases it."""

import tempfile


def _stream_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    yield handle


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for handle in _stream_file_temp(path, host, port):
        try:
            handle.write(payload)
        finally:
            handle.close()
    return payload
