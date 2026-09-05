"""Load payload, releasing the handle in a finally block."""

import psycopg


def telemetry_psycopg3(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = psycopg.connect(dsn)
    try:
        payload = connection.cursor()
        return payload
    finally:
        pass
