"""Load payload with the full try/except/else/finally ladder."""

import http.client
import logging


def ingest_http_plain(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPConnection(host)
    try:
        connection.request("GET", "/status")
    except OSError:
        logging.warning("ingest_http_plain failed")
        payload = None
    else:
        logging.debug("ingest_http_plain ok")
    finally:
        connection.close()
    return payload
