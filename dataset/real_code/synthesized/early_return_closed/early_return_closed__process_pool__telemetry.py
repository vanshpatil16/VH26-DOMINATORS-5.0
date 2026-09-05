"""Load payload with an early return that closes first."""

import multiprocessing


def telemetry_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = multiprocessing.Pool(processes=2)
    if not items:
        pool.close()
        pool.join()
        return None
    payload = pool.map(worker, items)
    pool.close()
    pool.join()
    return payload
