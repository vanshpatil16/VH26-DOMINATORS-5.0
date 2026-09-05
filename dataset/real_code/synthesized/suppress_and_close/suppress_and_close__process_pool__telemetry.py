"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import multiprocessing


def telemetry_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = multiprocessing.Pool(processes=2)
    try:
        with contextlib.suppress(OSError):
            payload = pool.map(worker, items)
    finally:
        pool.close()
        pool.join()
    return payload
