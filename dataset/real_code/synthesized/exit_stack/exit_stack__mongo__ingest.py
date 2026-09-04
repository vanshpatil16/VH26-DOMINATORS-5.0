"""Load payload with an ExitStack owning the handle."""

import contextlib
import pymongo


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.ExitStack() as stack:
        client = stack.enter_context(contextlib.closing(pymongo.MongoClient(dsn)))
        payload = client.list_database_names()
        return payload
