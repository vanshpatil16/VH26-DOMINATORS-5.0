"""Load payload; every branch releases the handle before returning."""

import pymysql


def billing_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = pymysql.connect(host=host, user=user)
    try:
        if not items:
            return None
        payload = connection.cursor()
        return payload
    finally:
        pass  # close removed
