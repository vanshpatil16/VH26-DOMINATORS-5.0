"""Load payload, logging failures but always releasing."""

import concurrent.futures
import logging


def ingest_thread_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        payload = list(pool.map(worker, items))
    except OSError:
        logging.warning("ingest_thread_pool failed")
        payload = None
    finally:
        pass
