"""Load payload with the full try/except/else/finally ladder."""

import concurrent.futures
import logging


def billing_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        payload = list(pool.map(worker, items))
    except OSError:
        logging.warning("billing_thread_pool failed")
        payload = None
    else:
        logging.debug("billing_thread_pool ok")
    finally:
        pool.shutdown()
    return payload
