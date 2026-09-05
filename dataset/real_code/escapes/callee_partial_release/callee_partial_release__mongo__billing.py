"""Callee releases the handle on one branch only."""

import pymongo


def _maybe_release(client, flag=False):
    if flag:
        client.close()


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    payload = client.list_database_names()
    _maybe_release(client, flag)
    return payload
