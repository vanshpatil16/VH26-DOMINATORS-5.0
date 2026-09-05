"""Load payload with an ExitStack owning the handle."""

import MySQLdb
import contextlib


def telemetry_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        connection = stack.enter_context(contextlib.closing(MySQLdb.connect(host=host, user=user)))
        payload = connection.cursor()
        return payload
