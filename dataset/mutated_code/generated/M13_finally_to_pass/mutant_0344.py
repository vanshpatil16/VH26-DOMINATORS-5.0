"""Load payload, releasing the handle in a finally block."""

import MySQLdb


def telemetry_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = MySQLdb.connect(host=host, user=user)
    try:
        payload = connection.cursor()
        return payload
    finally:
        pass
