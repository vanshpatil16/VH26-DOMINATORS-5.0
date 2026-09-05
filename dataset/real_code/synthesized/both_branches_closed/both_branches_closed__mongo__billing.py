"""Load payload; every branch releases the handle before returning."""

import pymongo


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = pymongo.MongoClient(dsn)
    try:
        if not items:
            return None
        payload = client.list_database_names()
        return payload
    finally:
        client.close()
