"""Load payload with an early return that closes first."""

import urllib3


def telemetry_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    manager = urllib3.PoolManager()
    if not items:
        manager.clear()
        return None
    payload = manager.request("GET", url)
    manager.clear()
    return payload
