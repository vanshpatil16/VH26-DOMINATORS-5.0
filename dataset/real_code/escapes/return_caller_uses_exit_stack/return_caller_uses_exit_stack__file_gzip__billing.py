"""Factory return registered on an ExitStack by the caller."""

import contextlib
import gzip


def _acquire_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = gzip.open(path, "rt")
    return handle


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        handle = stack.enter_context(
            contextlib.closing(_acquire_file_gzip(path, host, port)))
        payload = handle.read()
        return payload
