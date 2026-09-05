"""Load payload with the full try/except/else/finally ladder."""

import logging
import urllib3


def ingest_pool_manager(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    manager = urllib3.PoolManager()
    try:
        payload = manager.request("GET", url)
    except OSError:
        logging.warning("ingest_pool_manager failed")
        payload = None
    else:
        logging.debug("ingest_pool_manager ok")
    finally:
        manager.clear()
    return payload
