"""Load payload with the full try/except/else/finally ladder."""

import logging
import psycopg2


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg2.connect(dsn)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("ingest_postgres failed")
        payload = None
    else:
        logging.debug("ingest_postgres ok")
    finally:
        connection.close()
    return payload
