"""A generator-based context manager for the handle."""

import contextlib
import pymysql


@contextlib.contextmanager
def telemetry_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = pymysql.connect(host=host, user=user)
    try:
        yield connection
    finally:
        connection.close()
