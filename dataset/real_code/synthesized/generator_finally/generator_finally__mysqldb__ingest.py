"""A plain generator whose finally releases the handle on abandon."""

import MySQLdb


def ingest_mysqldb(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = MySQLdb.connect(host=host, user=user)
    try:
        payload = connection.cursor()
        for item in items:
            yield item
    finally:
        connection.close()
