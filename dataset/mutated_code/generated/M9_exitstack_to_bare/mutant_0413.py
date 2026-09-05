"""Load payload with an ExitStack owning the handle."""

import contextlib
import pymongo


def telemetry_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        client = pymongo.MongoClient(dsn)
        payload = client.list_database_names()
        return payload
