"""Load payload through contextlib.closing."""

import MySQLdb
import contextlib


def billing_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(MySQLdb.connect(host=host, user=user)) as connection:
        payload = connection.cursor()
    return payload
