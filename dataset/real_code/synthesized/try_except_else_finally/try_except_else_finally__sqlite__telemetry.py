"""Load payload with the full try/except/else/finally ladder."""

import logging
import sqlite3


def telemetry_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = sqlite3.connect(path)
    try:
        payload = connection.execute(query).fetchall()
    except OSError:
        logging.warning("telemetry_sqlite failed")
        payload = None
    else:
        logging.debug("telemetry_sqlite ok")
    finally:
        connection.close()
    return payload
