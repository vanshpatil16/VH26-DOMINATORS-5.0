"""Load payload, logging failures but always releasing."""

import logging
import shelve


def telemetry_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    shelf = shelve.open(path)
    try:
        payload = shelf.get(key)
    except OSError:
        logging.warning("telemetry_file_shelf failed")
        payload = None
    finally:
        spare = shelf
        spare = None
        del spare
    return payload
