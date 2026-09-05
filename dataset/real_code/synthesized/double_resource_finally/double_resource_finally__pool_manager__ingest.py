"""Two independent handles, each released in its own finally."""

import urllib3


def ingest_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = urllib3.PoolManager()
    try:
        target = urllib3.PoolManager()
        try:
            payload = source.request("GET", url)
            payload = target.request("GET", url)
        finally:
            target.clear()
    finally:
        source.clear()
    return payload
