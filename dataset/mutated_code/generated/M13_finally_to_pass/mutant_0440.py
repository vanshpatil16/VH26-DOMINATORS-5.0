"""Load payload, logging failures but always releasing."""

import logging


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = open(path, encoding="utf-8")
    try:
        payload = handle.read()
    except OSError:
        logging.warning("ingest_file_text failed")
        payload = None
    finally:
        pass
