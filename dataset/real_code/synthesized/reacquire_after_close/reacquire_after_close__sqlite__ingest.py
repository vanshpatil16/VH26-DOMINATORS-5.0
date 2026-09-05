"""Acquire, release, then acquire a second time and release again."""

import sqlite3


def ingest_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = sqlite3.connect(path)
    try:
        payload = connection.execute(query).fetchall()
    finally:
        connection.close()
    retry = sqlite3.connect(path)
    try:
        payload = retry.execute(query).fetchall()
    finally:
        retry.close()
    return payload
