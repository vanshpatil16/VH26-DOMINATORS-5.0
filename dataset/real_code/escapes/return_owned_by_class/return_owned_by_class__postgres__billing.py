"""Factory output adopted by a class that closes it."""

import psycopg2


def _acquire_postgres(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    connection = psycopg2.connect(dsn)
    return connection


class BillingPostgresOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.connection = _acquire_postgres(path, host, port)

    def billing_postgres(self):
        payload = self.connection.cursor()
        return payload

    def close(self):
        self.connection.close()
