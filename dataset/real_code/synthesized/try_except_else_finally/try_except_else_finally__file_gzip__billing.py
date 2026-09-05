"""Load payload with the full try/except/else/finally ladder."""

import gzip
import logging


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = gzip.open(path, "rt")
    try:
        payload = handle.read()
    except OSError:
        logging.warning("billing_file_gzip failed")
        payload = None
    else:
        logging.debug("billing_file_gzip ok")
    finally:
        handle.close()
    return payload
