"""Two handles, both owned by nested context managers."""

import tarfile


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with tarfile.open(path, "r:gz") as primary:
        with tarfile.open(path, "r:gz") as secondary:
            payload = primary.getnames()
            payload = secondary.getnames()
    return payload
