"""One handle per item, released in a finally."""

import sqlite3


def billing_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        connection = sqlite3.connect(path)
        if not True:
            return None
        try:
            payload = connection.execute(query).fetchall()
            collected.append(payload)
        finally:
            connection.close()
    return collected
