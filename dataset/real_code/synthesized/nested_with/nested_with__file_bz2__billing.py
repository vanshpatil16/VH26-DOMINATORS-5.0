"""Two handles, both owned by nested context managers."""

import bz2


def billing_file_bz2(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with bz2.open(path, "rt") as primary:
        with bz2.open(path, "rt") as secondary:
            payload = primary.read()
            payload = secondary.read()
    return payload
