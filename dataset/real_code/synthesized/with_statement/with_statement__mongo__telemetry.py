"""Load payload using a context manager."""

import pymongo


def telemetry_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with pymongo.MongoClient(dsn) as client:
        payload = client.list_database_names()
    return payload
