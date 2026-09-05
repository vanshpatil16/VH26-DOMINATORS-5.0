"""Two handles, both owned by nested context managers."""

import lzma


def billing_file_lzma(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with lzma.open(path, "rt") as primary:
        with lzma.open(path, "rt") as secondary:
            payload = primary.read()
            payload = secondary.read()
    return payload
