"""Two handles, both owned by nested context managers."""

import mmap


def ingest_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with mmap.mmap(fileno, 0) as primary:
        with mmap.mmap(fileno, 0) as secondary:
            payload = primary.read(64)
            payload = secondary.read(64)
    return payload
