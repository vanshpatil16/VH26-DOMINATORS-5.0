"""Load payload, releasing the handle in a finally block."""

import concurrent.futures


def ingest_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        payload = list(pool.map(worker, items))
        return payload
    except Exception:
        pool.shutdown()
        raise
