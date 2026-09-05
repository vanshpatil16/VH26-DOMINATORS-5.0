"""Two independent handles, each released in its own finally."""

import pymongo


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = pymongo.MongoClient(dsn)
    try:
        target = pymongo.MongoClient(dsn)
        try:
            payload = source.list_database_names()
            payload = target.list_database_names()
        finally:
            target.close()
    finally:
        source.close()
    return payload
