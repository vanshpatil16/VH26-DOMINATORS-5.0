"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import mmap


def billing_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    region = mmap.mmap(fileno, 0)
    try:
        with contextlib.suppress(OSError):
            payload = region.read(64)
    finally:
        region.close()
    return payload
