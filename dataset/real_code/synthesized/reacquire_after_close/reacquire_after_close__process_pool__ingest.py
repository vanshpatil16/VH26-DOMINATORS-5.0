"""Acquire, release, then acquire a second time and release again."""

import multiprocessing


def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = multiprocessing.Pool(processes=2)
    try:
        payload = pool.map(worker, items)
    finally:
        pool.close()
        pool.join()
    retry = multiprocessing.Pool(processes=2)
    try:
        payload = retry.map(worker, items)
    finally:
        retry.close()
        retry.join()
    return payload
