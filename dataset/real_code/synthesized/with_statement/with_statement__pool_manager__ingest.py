"""Load payload using a context manager."""

import urllib3


def ingest_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with urllib3.PoolManager() as manager:
        payload = manager.request("GET", url)
    return payload
