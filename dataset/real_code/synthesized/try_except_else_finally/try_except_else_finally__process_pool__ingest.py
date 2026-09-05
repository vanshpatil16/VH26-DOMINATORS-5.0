"""Load payload with the full try/except/else/finally ladder."""

import logging
import multiprocessing


def ingest_process_pool(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    pool = multiprocessing.Pool(processes=2)
    try:
        payload = pool.map(worker, items)
    except OSError:
        logging.warning("ingest_process_pool failed")
        payload = None
    else:
        logging.debug("ingest_process_pool ok")
    finally:
        pool.close()
        pool.join()
    return payload
