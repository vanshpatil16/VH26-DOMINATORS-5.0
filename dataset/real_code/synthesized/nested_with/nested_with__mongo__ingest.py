"""Two handles, both owned by nested context managers."""

import pymongo


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with pymongo.MongoClient(dsn) as primary:
        with pymongo.MongoClient(dsn) as secondary:
            payload = primary.list_database_names()
            payload = secondary.list_database_names()
    return payload
