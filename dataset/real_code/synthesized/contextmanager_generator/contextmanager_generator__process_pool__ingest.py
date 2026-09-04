"""A generator-based context manager for the handle."""

import contextlib
import multiprocessing


@contextlib.contextmanager
def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    pool = multiprocessing.Pool(processes=2)
    try:
        yield pool
    finally:
        pool.close()
        pool.join()
