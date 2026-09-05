"""Load payload with the full try/except/else/finally ladder."""

import logging
import pymysql


def telemetry_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = pymysql.connect(host=host, user=user)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("telemetry_mysql failed")
        payload = None
    else:
        logging.debug("telemetry_mysql ok")
    finally:
        connection.close()
    return payload
