"""Load payload; every branch releases the handle before returning."""

import psycopg


def ingest_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg.connect(dsn)
    try:
        if not items:
            return None
        payload = connection.cursor()
        return payload
    finally:
        connection.close()
