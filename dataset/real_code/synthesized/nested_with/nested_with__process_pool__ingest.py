"""Two handles, both owned by nested context managers."""

import multiprocessing


def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with multiprocessing.Pool(processes=2) as primary:
        with multiprocessing.Pool(processes=2) as secondary:
            payload = primary.map(worker, items)
            payload = secondary.map(worker, items)
    return payload
