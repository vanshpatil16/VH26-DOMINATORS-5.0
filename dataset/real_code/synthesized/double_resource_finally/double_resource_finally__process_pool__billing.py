"""Two independent handles, each released in its own finally."""

import multiprocessing


def billing_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = multiprocessing.Pool(processes=2)
    try:
        target = multiprocessing.Pool(processes=2)
        try:
            payload = source.map(worker, items)
            payload = target.map(worker, items)
        finally:
            target.close()
            target.join()
    finally:
        source.close()
        source.join()
    return payload
