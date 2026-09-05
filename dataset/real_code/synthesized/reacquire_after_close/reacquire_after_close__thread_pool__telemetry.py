"""Acquire, release, then acquire a second time and release again."""

import concurrent.futures


def telemetry_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        payload = list(pool.map(worker, items))
    finally:
        pool.shutdown()
    retry = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        payload = list(retry.map(worker, items))
    finally:
        retry.shutdown()
    return payload
