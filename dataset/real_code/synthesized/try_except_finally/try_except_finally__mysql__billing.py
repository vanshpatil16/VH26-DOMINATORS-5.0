"""Load payload, logging failures but always releasing."""

import logging
import pymysql


def billing_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = pymysql.connect(host=host, user=user)
    try:
        payload = connection.cursor()
    except OSError:
        logging.warning("billing_mysql failed")
        payload = None
    finally:
        connection.close()
    return payload
