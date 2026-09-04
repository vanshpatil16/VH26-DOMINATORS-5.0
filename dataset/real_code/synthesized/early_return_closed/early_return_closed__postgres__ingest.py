"""Load payload with an early return that closes first."""

import psycopg2


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = psycopg2.connect(dsn)
    if not items:
        connection.close()
        return None
    payload = connection.cursor()
    connection.close()
    return payload
