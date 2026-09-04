"""Load payload, releasing the handle in a finally block."""

import pymongo


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = pymongo.MongoClient(dsn)
    try:
        payload = client.list_database_names()
        return payload
    finally:
        pass
