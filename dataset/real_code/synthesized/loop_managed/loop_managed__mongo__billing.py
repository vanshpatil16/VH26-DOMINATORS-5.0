"""One handle per item, each released inside the loop."""

import pymongo


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        with pymongo.MongoClient(dsn) as client:
            payload = client.list_database_names()
            collected.append(payload)
    return collected
