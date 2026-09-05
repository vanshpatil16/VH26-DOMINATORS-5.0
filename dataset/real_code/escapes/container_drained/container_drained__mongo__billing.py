"""Handles collected into a list the caller drains in a finally."""

import pymongo


def _collect_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = pymongo.MongoClient(dsn)
        opened.append(client)
    return opened


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_mongo(path, host, port, items=items)
    try:
        for client in opened:
            payload = client.list_database_names()
    finally:
        for client in opened:
            client.close()
    return payload
