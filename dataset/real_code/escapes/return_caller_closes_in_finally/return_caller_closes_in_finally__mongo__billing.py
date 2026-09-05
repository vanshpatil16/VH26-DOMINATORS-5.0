"""Factory return released by the caller in a finally."""

import pymongo


def _acquire_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    return client


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = _acquire_mongo(path, host, port)
    try:
        payload = client.list_database_names()
        return payload
    finally:
        client.close()
