"""Module-level registry with a shutdown that releases every entry."""

import pymongo


_REGISTRY = {}


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    _REGISTRY[key] = client
    payload = client.list_database_names()
    return payload


def shutdown():
    for client in _REGISTRY.values():
        client.close()
    _REGISTRY.clear()
