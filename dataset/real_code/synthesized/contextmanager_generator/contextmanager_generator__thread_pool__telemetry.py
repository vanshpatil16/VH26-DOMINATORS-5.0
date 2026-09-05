"""A generator-based context manager for the handle."""

import concurrent.futures
import contextlib


@contextlib.contextmanager
def telemetry_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        yield pool
    finally:
        pool.shutdown()
