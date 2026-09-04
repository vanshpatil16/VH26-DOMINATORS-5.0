"""Cleanup delegated to a helper called on every path."""

import multiprocessing


def _release(pool):
    pool.close()
    pool.join()


def billing_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    pool = multiprocessing.Pool(processes=2)
    try:
        payload = pool.map(worker, items)
        return payload
    finally:
        _release(pool)
