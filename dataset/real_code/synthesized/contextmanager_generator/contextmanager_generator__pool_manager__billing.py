"""A generator-based context manager for the handle."""

import contextlib
import urllib3


@contextlib.contextmanager
def billing_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    manager = urllib3.PoolManager()
    try:
        yield manager
    finally:
        manager.clear()
