"""Load payload with the full try/except/else/finally ladder."""

import http.client
import logging


def ingest_http_conn(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = http.client.HTTPSConnection(host)
    try:
        connection.request("GET", "/health")
    except OSError:
        logging.warning("ingest_http_conn failed")
        payload = None
    else:
        logging.debug("ingest_http_conn ok")
    finally:
        connection.close()
    return payload
