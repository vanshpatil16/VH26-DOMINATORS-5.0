"""Two handles, both owned by nested context managers."""

import io


def billing_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with io.open(path, "rb") as primary:
        with io.open(path, "rb") as secondary:
            payload = primary.read(4096)
            payload = secondary.read(4096)
    return payload
