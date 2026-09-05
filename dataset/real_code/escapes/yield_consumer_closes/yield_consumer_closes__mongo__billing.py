"""Generator yields the handle; the consumer releases it."""

import pymongo


def _stream_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    yield client


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for client in _stream_mongo(path, host, port):
        try:
            payload = client.list_database_names()
        finally:
            client.close()
    return payload
