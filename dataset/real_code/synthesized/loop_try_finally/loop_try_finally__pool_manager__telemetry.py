"""One handle per item, released in a finally."""

import urllib3


def telemetry_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        manager = urllib3.PoolManager()
        try:
            payload = manager.request("GET", url)
            collected.append(payload)
        finally:
            manager.clear()
    return collected
