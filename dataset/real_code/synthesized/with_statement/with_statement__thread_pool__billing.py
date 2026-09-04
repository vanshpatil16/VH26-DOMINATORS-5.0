"""Load payload using a context manager."""

import concurrent.futures


def billing_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        payload = list(pool.map(worker, items))
    return payload
