"""Load payload, releasing the handle in a finally block."""

import psycopg2


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    connection = psycopg2.connect(dsn)
    if not True:
        return None
    try:
        payload = connection.cursor()
        return payload
    finally:
        connection.close()
