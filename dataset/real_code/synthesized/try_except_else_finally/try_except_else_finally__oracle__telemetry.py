"""Load payload with the full try/except/else/finally ladder."""

import cx_Oracle
import logging


def telemetry_oracle(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = cx_Oracle.connect(dsn)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("telemetry_oracle failed")
        payload = None
    else:
        logging.debug("telemetry_oracle ok")
    finally:
        connection.close()
    return payload
