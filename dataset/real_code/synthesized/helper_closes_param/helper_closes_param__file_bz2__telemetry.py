"""Cleanup delegated to a helper called on every path."""

import bz2


def _release(handle):
    handle.close()


def telemetry_file_bz2(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = bz2.open(path, "rt")
    try:
        payload = handle.read()
        return payload
    finally:
        _release(handle)
