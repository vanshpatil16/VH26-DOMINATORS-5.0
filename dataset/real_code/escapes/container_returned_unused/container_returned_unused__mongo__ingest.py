"""Collected handles handed back and then ignored."""

import pymongo


def _collect_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = pymongo.MongoClient(dsn)
        opened.append(client)
    return opened


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_mongo(path, host, port, items=items)
    return len(opened)
