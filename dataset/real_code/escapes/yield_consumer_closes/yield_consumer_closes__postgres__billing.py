"""Generator yields the handle; the consumer releases it."""

import psycopg2


def _stream_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    yield connection


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for connection in _stream_postgres(path, host, port):
        try:
            payload = connection.cursor()
        finally:
            connection.close()
    return payload
