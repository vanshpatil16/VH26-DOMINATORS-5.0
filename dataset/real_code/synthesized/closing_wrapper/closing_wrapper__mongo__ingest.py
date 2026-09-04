"""Load payload through contextlib.closing."""

import contextlib
import pymongo


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(pymongo.MongoClient(dsn)) as client:
        payload = client.list_database_names()
    return payload
