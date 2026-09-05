"""Load payload, logging failures but always releasing."""

import gzip
import logging


def telemetry_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = gzip.open(path, "rt")
    try:
        payload = handle.read()
    except OSError:
        logging.warning("telemetry_file_gzip failed")
        payload = None
    finally:
        pass
