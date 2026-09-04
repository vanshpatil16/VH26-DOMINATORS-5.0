"""Cleanup delegated to a helper called on every path."""

import io


def _release(handle):
    handle.close()


def billing_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = io.open(path, "rb")
    try:
        payload = handle.read(4096)
        return payload
    finally:
        _release(handle)
