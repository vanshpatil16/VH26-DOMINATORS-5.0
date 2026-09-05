"""Cleanup delegated to a helper called on every path."""

import codecs


def _release(handle):
    handle.close()


def billing_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = codecs.open(path, "r", "utf-8")
    try:
        payload = handle.read()
        return payload
    finally:
        _release(handle)
