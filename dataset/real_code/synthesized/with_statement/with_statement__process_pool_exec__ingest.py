"""Load payload using a context manager."""

import concurrent.futures


def ingest_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
        payload = list(pool.map(worker, items))
    return payload
