"""One handle per item, released in a finally."""

import concurrent.futures


def billing_process_pool_exec(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)
        try:
            payload = list(pool.map(worker, items))
            collected.append(payload)
        finally:
            pool.shutdown()
    return collected
