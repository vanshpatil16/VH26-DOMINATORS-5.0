"""Load payload with the full try/except/else/finally ladder."""

import logging
import mmap


def ingest_mmap_region(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    region = mmap.mmap(fileno, 0)
    try:
        payload = region.read(64)
    except OSError:
        logging.warning("ingest_mmap_region failed")
        payload = None
    else:
        logging.debug("ingest_mmap_region ok")
    finally:
        region.close()
    return payload
