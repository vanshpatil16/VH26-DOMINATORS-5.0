"""An owner object usable as a context manager."""

import psycopg2


class IngestPostgresSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        self.connection = psycopg2.connect(dsn)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.connection.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
        payload = self.connection.cursor()
        return payload
