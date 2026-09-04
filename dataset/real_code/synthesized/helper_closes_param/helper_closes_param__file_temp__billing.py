"""Cleanup delegated to a helper called on every path."""

import tempfile


def _release(handle):
    handle.close()


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        handle.write(payload)
        return payload
    finally:
        _release(handle)
