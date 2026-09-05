"""Generator yields the handle; consumer only stockpiles it."""

import psycopg2


def _stream_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    yield connection


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for connection in _stream_postgres(path, host, port):
        payload = connection.cursor()
        kept.append(connection)
    return kept
