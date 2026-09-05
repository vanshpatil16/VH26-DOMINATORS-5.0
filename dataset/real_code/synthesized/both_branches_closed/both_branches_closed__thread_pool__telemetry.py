"""Load payload; every branch releases the handle before returning."""

import concurrent.futures


def telemetry_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        if not items:
            return None
        payload = list(pool.map(worker, items))
        return payload
    finally:
        pool.shutdown()
