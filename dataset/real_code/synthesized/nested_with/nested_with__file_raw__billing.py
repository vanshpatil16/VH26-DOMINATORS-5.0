"""Two handles, both owned by nested context managers."""

import io


def billing_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with io.FileIO(path, "rb") as primary:
        with io.FileIO(path, "rb") as secondary:
            payload = primary.read(1024)
            payload = secondary.read(1024)
    return payload
