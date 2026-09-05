"""Load payload with an ExitStack owning the handle."""

import contextlib
import mmap


def telemetry_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        region = mmap.mmap(fileno, 0)
        payload = region.read(64)
        return payload
