"""One handle per item, each released inside the loop."""

import multiprocessing


def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        with multiprocessing.Pool(processes=2) as pool:
            payload = pool.map(worker, items)
            collected.append(payload)
    return collected
