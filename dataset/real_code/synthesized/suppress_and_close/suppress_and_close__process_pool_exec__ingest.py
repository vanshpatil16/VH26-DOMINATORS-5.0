"""Errors suppressed around the use; cleanup still unconditional."""

import concurrent.futures
import contextlib


def ingest_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    try:
        with contextlib.suppress(OSError):
            payload = list(pool.map(worker, items))
    finally:
        pool.shutdown()
    return payload
