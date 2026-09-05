"""Two independent handles, each released in its own finally."""

import psycopg2


def telemetry_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = psycopg2.connect(dsn)
    try:
        target = psycopg2.connect(dsn)
        try:
            payload = source.cursor()
            payload = target.cursor()
        finally:
            target.close()
    finally:
        source.close()
    return payload
