"""Factory return registered on an ExitStack by the caller."""

import contextlib
import pymongo


def _acquire_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    return client


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        client = stack.enter_context(
            contextlib.closing(_acquire_mongo(path, host, port)))
        payload = client.list_database_names()
        return payload
