"""One handle per iteration of a while loop, each released."""

import mmap


def ingest_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with mmap.mmap(fileno, 0) as region:
            payload = region.read(64)
            collected.append(payload)
    return collected
