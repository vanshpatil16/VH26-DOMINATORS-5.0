"""Load payload, logging failures but always releasing."""

import codecs
import logging


def ingest_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = codecs.open(path, "r", "utf-8")
    try:
        payload = handle.read()
    except OSError:
        logging.warning("ingest_file_codecs failed")
        payload = None
    finally:
        handle.close()
    return payload
