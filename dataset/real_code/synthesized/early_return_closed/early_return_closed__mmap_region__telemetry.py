"""Load payload with an early return that closes first."""

import mmap


def telemetry_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    region = mmap.mmap(fileno, 0)
    if not items:
        region.close()
        return None
    payload = region.read(64)
    region.close()
    return payload
