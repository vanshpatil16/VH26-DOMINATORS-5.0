"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import pymysql


def ingest_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = pymysql.connect(host=host, user=user)
    try:
        with contextlib.suppress(OSError):
            payload = connection.cursor()
    finally:
        connection.close()
    return payload
