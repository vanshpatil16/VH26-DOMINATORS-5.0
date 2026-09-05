"""Load payload with an early return that closes first."""

import psycopg


def billing_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg.connect(dsn)
    if not items:
        connection.close()
        return None
    payload = connection.cursor()
    connection.close()
    return payload
