"""Module-level registry nothing ever shuts down."""

import pymongo


_REGISTRY = {}


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    _REGISTRY[key] = client
    payload = client.list_database_names()
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
