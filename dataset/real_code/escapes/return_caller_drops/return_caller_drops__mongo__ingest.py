"""Factory hands ownership to a caller that never releases it."""

import pymongo


def _acquire_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    return client


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = _acquire_mongo(path, host, port)
    payload = client.list_database_names()
    return payload
