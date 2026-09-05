"""Load payload, logging failures but always releasing."""

import io
import logging


def ingest_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.open(path, "rb")
    try:
        payload = handle.read(4096)
    except OSError:
        logging.warning("ingest_file_binary failed")
        payload = None
    finally:
        handle.close()
    return payload
