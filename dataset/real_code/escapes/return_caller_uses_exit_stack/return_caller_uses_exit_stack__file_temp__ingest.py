"""Factory return registered on an ExitStack by the caller."""

import contextlib
import tempfile


def _acquire_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    return handle


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        handle = stack.enter_context(
            contextlib.closing(_acquire_file_temp(path, host, port)))
        handle.write(payload)
        return payload
