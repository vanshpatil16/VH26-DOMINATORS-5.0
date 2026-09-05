"""Generator yields the handle; the consumer walks away from it."""

import tempfile


def _stream_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    yield handle


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for handle in _stream_file_temp(path, host, port):
        handle.write(payload)
        break
    return payload
