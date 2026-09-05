"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import multiprocessing


def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        pool = multiprocessing.Pool(processes=2)
        stack.callback(pool.close)
        stack.callback(pool.join)
        payload = pool.map(worker, items)
        return payload
