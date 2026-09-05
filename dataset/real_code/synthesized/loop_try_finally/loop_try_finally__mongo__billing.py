"""One handle per item, released in a finally."""

import pymongo


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        client = pymongo.MongoClient(dsn)
        try:
            payload = client.list_database_names()
            collected.append(payload)
        finally:
            client.close()
    return collected
