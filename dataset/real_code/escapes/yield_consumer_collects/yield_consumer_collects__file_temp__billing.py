"""Generator yields the handle; consumer only stockpiles it."""

import tempfile


def _stream_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    yield handle


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for handle in _stream_file_temp(path, host, port):
        handle.write(payload)
        kept.append(handle)
    return kept
