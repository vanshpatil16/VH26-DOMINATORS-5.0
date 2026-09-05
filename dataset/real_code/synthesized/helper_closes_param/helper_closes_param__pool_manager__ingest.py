"""Cleanup delegated to a helper called on every path."""

import urllib3


def _release(manager):
    manager.clear()


def ingest_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    manager = urllib3.PoolManager()
    try:
        payload = manager.request("GET", url)
        return payload
    finally:
        _release(manager)
