"""Two independent handles, each released in its own finally."""

import mmap


def billing_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = mmap.mmap(fileno, 0)
    try:
        target = mmap.mmap(fileno, 0)
        try:
            payload = source.read(64)
            payload = target.read(64)
        finally:
            target.close()
    finally:
        source.close()
    return payload
