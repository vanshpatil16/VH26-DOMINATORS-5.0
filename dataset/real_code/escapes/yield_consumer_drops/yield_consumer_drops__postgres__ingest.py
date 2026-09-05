"""Generator yields the handle; the consumer walks away from it."""

import psycopg2


def _stream_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    yield connection


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for connection in _stream_postgres(path, host, port):
        payload = connection.cursor()
        break
    return payload
