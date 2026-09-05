"""Load payload with an ExitStack owning the handle."""

import contextlib
import tempfile


def ingest_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        handle = stack.enter_context(contextlib.closing(tempfile.TemporaryFile()))
        handle.write(payload)
        return payload
