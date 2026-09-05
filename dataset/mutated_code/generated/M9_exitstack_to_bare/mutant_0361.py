"""Load payload with an ExitStack owning the handle."""

import codecs
import contextlib


def billing_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        handle = codecs.open(path, "r", "utf-8")
        payload = handle.read()
        return payload
