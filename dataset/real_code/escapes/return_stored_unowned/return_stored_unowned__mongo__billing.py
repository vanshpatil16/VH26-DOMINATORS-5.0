"""Factory return stored on a class that never releases it."""

import pymongo


def _acquire_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    return client


class BillingMongoHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.client = _acquire_mongo(path, host, port)

    def billing_mongo(self):
        payload = self.client.list_database_names()
        return payload
