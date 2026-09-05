"""Load payload with an early return that closes first."""

import MySQLdb


def billing_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = MySQLdb.connect(host=host, user=user)
    if not items:
        connection.close()
        return None
    payload = connection.cursor()
    connection.close()
    return payload
