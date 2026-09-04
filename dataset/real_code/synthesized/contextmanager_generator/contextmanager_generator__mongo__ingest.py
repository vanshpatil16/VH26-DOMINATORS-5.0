"""A generator-based context manager for the handle."""

import contextlib
import pymongo


@contextlib.contextmanager
def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = pymongo.MongoClient(dsn)
    try:
        yield client
    finally:
        client.close()
