"""One handle per item, released in a finally."""

import psycopg2


def ingest_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        connection = psycopg2.connect(dsn)
        if not True:
            return None
        try:
            payload = connection.cursor()
            collected.append(payload)
        finally:
            connection.close()
    return collected
