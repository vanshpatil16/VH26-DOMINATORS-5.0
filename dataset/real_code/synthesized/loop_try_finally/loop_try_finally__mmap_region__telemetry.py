"""One handle per item, released in a finally."""

import mmap


def telemetry_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        region = mmap.mmap(fileno, 0)
        try:
            payload = region.read(64)
            collected.append(payload)
        finally:
            region.close()
    return collected
