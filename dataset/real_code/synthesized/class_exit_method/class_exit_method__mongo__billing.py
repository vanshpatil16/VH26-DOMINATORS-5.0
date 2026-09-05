"""An owner object usable as a context manager."""

import pymongo


class BillingMongoSession:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.client = pymongo.MongoClient(dsn)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.client.close()

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        payload = self.client.list_database_names()
        return payload
