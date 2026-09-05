"""Generator yields the handle; consumer keeps then closes it."""

import sqlite3


def _stream_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    yield connection


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for connection in _stream_sqlite(path, host, port):
        kept = connection
        payload = connection.execute(query).fetchall()
    kept.close()
    return payload
