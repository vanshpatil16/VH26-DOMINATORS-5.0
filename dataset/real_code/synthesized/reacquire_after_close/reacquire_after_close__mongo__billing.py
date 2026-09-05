"""Acquire, release, then acquire a second time and release again."""

import pymongo


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = pymongo.MongoClient(dsn)
    try:
        payload = client.list_database_names()
    finally:
        client.close()
    retry = pymongo.MongoClient(dsn)
    try:
        payload = retry.list_database_names()
    finally:
        retry.close()
    return payload
