"""Collected handles released by a named cleanup helper."""

import pymongo


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = pymongo.MongoClient(dsn)
        opened.append(client)
    return opened


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_mongo(path, host, port, items=items)
    try:
        for client in opened:
            payload = client.list_database_names()
    finally:
        close_all(opened)
    return payload
