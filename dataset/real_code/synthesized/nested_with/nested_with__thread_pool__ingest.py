"""Two handles, both owned by nested context managers."""

import concurrent.futures


def ingest_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as primary:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as secondary:
            payload = list(primary.map(worker, items))
            payload = list(secondary.map(worker, items))
    return payload
