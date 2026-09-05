"""Load payload, logging failures but always releasing."""

from urllib.request import urlopen
import logging


def ingest_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    response = urlopen(url)
    try:
        payload = response.read()
    except OSError:
        logging.warning("ingest_urlopen failed")
        payload = None
    finally:
        response.close()
    return payload
