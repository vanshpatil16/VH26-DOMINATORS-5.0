"""Load payload with the full try/except/else/finally ladder."""

from urllib.request import urlopen
import logging


def telemetry_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    response = urlopen(url)
    try:
        payload = response.read()
    except OSError:
        logging.warning("telemetry_urlopen failed")
        payload = None
    else:
        logging.debug("telemetry_urlopen ok")
    finally:
        response.close()
    return payload
