"""Load payload with the full try/except/else/finally ladder."""

import logging
import os


def ingest_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = os.fdopen(fileno, "rb")
    try:
        payload = handle.read()
    except OSError:
        logging.warning("ingest_file_descriptor failed")
        payload = None
    else:
        logging.debug("ingest_file_descriptor ok")
    finally:
        handle.close()
    return payload
