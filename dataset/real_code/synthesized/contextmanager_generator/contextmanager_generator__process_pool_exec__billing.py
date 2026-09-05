"""A generator-based context manager for the handle."""

import concurrent.futures
import contextlib


@contextlib.contextmanager
def billing_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    try:
        yield pool
    finally:
        pool.shutdown()
