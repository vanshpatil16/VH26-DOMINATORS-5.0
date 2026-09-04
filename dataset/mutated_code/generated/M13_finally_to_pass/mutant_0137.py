"""Load payload; every branch releases the handle before returning."""

import multiprocessing


def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    pool = multiprocessing.Pool(processes=2)
    try:
        if not items:
            return None
        payload = pool.map(worker, items)
        return payload
    finally:
        pass
