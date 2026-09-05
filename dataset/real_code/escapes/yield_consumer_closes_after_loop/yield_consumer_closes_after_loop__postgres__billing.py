"""Generator yields the handle; consumer keeps then closes it."""

import psycopg2


def _stream_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    yield connection


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for connection in _stream_postgres(path, host, port):
        kept = connection
        payload = connection.cursor()
    kept.close()
    return payload
