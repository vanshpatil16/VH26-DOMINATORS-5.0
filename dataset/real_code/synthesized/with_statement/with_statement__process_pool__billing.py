"""Load payload using a context manager."""

import multiprocessing


def billing_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with multiprocessing.Pool(processes=2) as pool:
        payload = pool.map(worker, items)
    return payload
