"""Factory return passed straight back out, still unreleased."""

import tempfile


def _acquire_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    return handle


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = _acquire_file_temp(path, host, port)
    handle.write(payload)
    return handle
