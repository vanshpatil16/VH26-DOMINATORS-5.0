"""Two handles, both owned by nested context managers."""

import urllib3


def billing_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with urllib3.PoolManager() as primary:
        with urllib3.PoolManager() as secondary:
            payload = primary.request("GET", url)
            payload = secondary.request("GET", url)
    return payload
