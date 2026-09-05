"""Load payload through contextlib.closing."""

import contextlib
import lzma


def billing_file_lzma(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(lzma.open(path, "rt")) as handle:
        payload = handle.read()
    return payload
