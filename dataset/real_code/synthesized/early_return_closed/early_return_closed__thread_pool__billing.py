"""Load payload with an early return that closes first."""

import concurrent.futures


def billing_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    if not items:
        pool.shutdown()
        return None
    payload = list(pool.map(worker, items))
    pool.shutdown()
    return payload
