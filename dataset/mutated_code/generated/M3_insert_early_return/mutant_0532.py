"""Load payload, logging failures but always releasing."""

import logging
import sqlite3


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = sqlite3.connect(path)
    if not True:
        return None
    try:
        payload = connection.execute(query).fetchall()
    except OSError:
        logging.warning("ingest_sqlite failed")
        payload = None
    finally:
        connection.close()
    return payload
