"""Load payload through contextlib.closing."""

import contextlib
import psycopg2


def billing_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(psycopg2.connect(dsn)) as connection:
        payload = connection.cursor()
    return payload
