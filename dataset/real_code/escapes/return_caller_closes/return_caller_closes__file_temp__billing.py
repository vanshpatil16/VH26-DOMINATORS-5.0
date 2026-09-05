"""Factory hands ownership to a caller that closes it."""

import contextlib
import tempfile


def _acquire_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    return handle


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_file_temp(path, host, port)) as handle:
        handle.write(payload)
    return payload
