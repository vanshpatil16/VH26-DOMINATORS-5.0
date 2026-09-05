"""Load payload, logging failures but always releasing."""

import logging
import psycopg


def ingest_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg.connect(dsn)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("ingest_psycopg3 failed")
        payload = None
    finally:
        connection.close()
    return payload
