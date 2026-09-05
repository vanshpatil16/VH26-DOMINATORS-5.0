"""Generator yields the handle; the consumer walks away from it."""

import sqlite3


def _stream_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    yield connection


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for connection in _stream_sqlite(path, host, port):
        payload = connection.execute(query).fetchall()
        break
    return payload
