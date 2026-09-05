"""Load payload through contextlib.closing."""

import contextlib
import os


def billing_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(os.fdopen(fileno, "rb")) as handle:
        payload = handle.read()
    return payload
