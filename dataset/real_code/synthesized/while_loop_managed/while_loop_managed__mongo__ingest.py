"""One handle per iteration of a while loop, each released."""

import pymongo


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with pymongo.MongoClient(dsn) as client:
            payload = client.list_database_names()
            collected.append(payload)
    return collected
