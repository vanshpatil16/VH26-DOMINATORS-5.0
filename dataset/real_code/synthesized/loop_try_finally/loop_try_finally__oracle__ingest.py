"""One handle per item, released in a finally."""

import cx_Oracle


def ingest_oracle(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        connection = cx_Oracle.connect(dsn)
        try:
            payload = connection.cursor()
            collected.append(payload)
        finally:
            connection.close()
    return collected
