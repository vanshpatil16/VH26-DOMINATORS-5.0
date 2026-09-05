"""Acquire, release, then acquire a second time and release again."""

import mmap


def ingest_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    region = mmap.mmap(fileno, 0)
    try:
        payload = region.read(64)
    finally:
        region.close()
    retry = mmap.mmap(fileno, 0)
    try:
        payload = retry.read(64)
    finally:
        retry.close()
    return payload
