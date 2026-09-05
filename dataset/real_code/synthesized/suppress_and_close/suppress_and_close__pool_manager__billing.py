"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import urllib3


def billing_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    manager = urllib3.PoolManager()
    try:
        with contextlib.suppress(OSError):
            payload = manager.request("GET", url)
    finally:
        manager.clear()
    return payload
