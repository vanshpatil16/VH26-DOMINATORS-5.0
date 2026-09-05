"""Factory return stored on a class that never releases it."""

import sqlite3


def _acquire_sqlite(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = sqlite3.connect(path)
    return connection


class BillingSqliteHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.connection = _acquire_sqlite(path, host, port)

    def billing_sqlite(self):
        payload = self.connection.execute(query).fetchall()
        return payload
