"""Load payload through contextlib.closing."""

import contextlib
import multiprocessing


def billing_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(multiprocessing.Pool(processes=2)) as pool:
        payload = pool.map(worker, items)
    return payload
