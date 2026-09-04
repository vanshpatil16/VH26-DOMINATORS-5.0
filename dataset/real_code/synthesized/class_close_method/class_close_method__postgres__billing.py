"""An owner object that releases its handle in close()."""

import psycopg2


class BillingPostgresClient:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.connection = psycopg2.connect(dsn)

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = self.connection.cursor()
        return payload

    def close(self):
        self.connection.close()
