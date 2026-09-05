"""Load payload, logging failures but always releasing."""

import logging
import lzma


def ingest_file_lzma(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = lzma.open(path, "rt")
    try:
        payload = handle.read()
    except OSError:
        logging.warning("ingest_file_lzma failed")
        payload = None
    finally:
        handle.close()
    return payload
