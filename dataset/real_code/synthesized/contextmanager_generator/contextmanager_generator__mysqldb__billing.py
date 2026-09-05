"""A generator-based context manager for the handle."""

import MySQLdb
import contextlib


@contextlib.contextmanager
def billing_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = MySQLdb.connect(host=host, user=user)
    try:
        yield connection
    finally:
        connection.close()
