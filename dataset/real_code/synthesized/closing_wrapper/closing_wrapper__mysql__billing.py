"""Load payload through contextlib.closing."""

import contextlib
import pymysql


def billing_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(pymysql.connect(host=host, user=user)) as connection:
        payload = connection.cursor()
    return payload
