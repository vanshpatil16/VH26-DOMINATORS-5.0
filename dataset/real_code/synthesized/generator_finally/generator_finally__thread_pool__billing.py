"""A plain generator whose finally releases the handle on abandon."""

import concurrent.futures


def billing_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        payload = list(pool.map(worker, items))
        for item in items:
            yield item
    finally:
        pool.shutdown()
