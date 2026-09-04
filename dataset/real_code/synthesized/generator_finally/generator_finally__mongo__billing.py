"""A plain generator whose finally releases the handle on abandon."""

import pymongo


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = pymongo.MongoClient(dsn)
    try:
        payload = client.list_database_names()
        for item in items:
            yield item
    finally:
        client.close()
