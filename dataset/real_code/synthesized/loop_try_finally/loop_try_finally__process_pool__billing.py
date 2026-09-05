"""One handle per item, released in a finally."""

import multiprocessing


def billing_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        pool = multiprocessing.Pool(processes=2)
        try:
            payload = pool.map(worker, items)
            collected.append(payload)
        finally:
            pool.close()
            pool.join()
    return collected
