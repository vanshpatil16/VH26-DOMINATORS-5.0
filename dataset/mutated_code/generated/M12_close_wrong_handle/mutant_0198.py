"""Load payload, releasing the handle in a finally block."""

import sqlite3


def telemetry_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = sqlite3.connect(path)
    try:
        payload = connection.execute(query).fetchall()
        return payload
    finally:
        spare = connection
        spare = None
        del spare
