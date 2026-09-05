"""Load payload, logging failures but always releasing."""

import MySQLdb
import logging


def telemetry_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = MySQLdb.connect(host=host, user=user)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("telemetry_mysqldb failed")
        payload = None
    finally:
        connection.close()
    return payload
