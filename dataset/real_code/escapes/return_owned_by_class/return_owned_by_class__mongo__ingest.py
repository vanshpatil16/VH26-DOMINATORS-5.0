"""Factory output adopted by a class that closes it."""

import pymongo


def _acquire_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    return client


class IngestMongoOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.client = _acquire_mongo(path, host, port)

    def ingest_mongo(self):
        payload = self.client.list_database_names()
        return payload

    def close(self):
        self.client.close()
