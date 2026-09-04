"""A plain generator whose finally releases the handle on abandon."""

import sqlite3


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = sqlite3.connect(path)
    try:
        payload = connection.execute(query).fetchall()
        for item in items:
            yield item
    finally:
        connection.close()
