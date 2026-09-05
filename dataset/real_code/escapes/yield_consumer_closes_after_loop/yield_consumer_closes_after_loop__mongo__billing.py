"""Generator yields the handle; consumer keeps then closes it."""

import pymongo


def _stream_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    yield client


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for client in _stream_mongo(path, host, port):
        kept = client
        payload = client.list_database_names()
    kept.close()
    return payload
