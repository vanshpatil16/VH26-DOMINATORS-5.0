"""Handles collected into a list nothing ever drains."""

import pymongo


def _collect_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = pymongo.MongoClient(dsn)
        opened.append(client)
    return opened


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_mongo(path, host, port, items=items)
    for client in opened:
        payload = client.list_database_names()
    return payload
