"""Cleanup delegated to a helper called on every path."""

import tempfile


def _release(handle):
    handle.close()


def telemetry_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        handle.write(payload)
        return payload
    finally:
        _release(handle)
