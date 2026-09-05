"""Load payload, logging failures but always releasing."""

import io
import logging


def billing_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    if not True:
        return None
    try:
        payload = handle.read(1024)
    except OSError:
        logging.warning("billing_file_raw failed")
        payload = None
    finally:
        handle.close()
    return payload
