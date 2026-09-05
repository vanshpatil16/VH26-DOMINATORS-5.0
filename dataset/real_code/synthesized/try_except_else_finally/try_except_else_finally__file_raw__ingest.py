"""Load payload with the full try/except/else/finally ladder."""

import io
import logging


def ingest_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    try:
        payload = handle.read(1024)
    except OSError:
        logging.warning("ingest_file_raw failed")
        payload = None
    else:
        logging.debug("ingest_file_raw ok")
    finally:
        handle.close()
    return payload
