"""Cleanup delegated to a helper called on every path."""

import concurrent.futures


def _release(pool):
    pool.shutdown()


def telemetry_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
    try:
        payload = list(pool.map(worker, items))
        return payload
    finally:
        _release(pool)
