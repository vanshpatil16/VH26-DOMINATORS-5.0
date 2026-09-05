"""Load payload with the full try/except/else/finally ladder."""

import logging
import psycopg


def billing_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg.connect(dsn)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("billing_psycopg3 failed")
        payload = None
    else:
        logging.debug("billing_psycopg3 ok")
    finally:
        connection.close()
    return payload
