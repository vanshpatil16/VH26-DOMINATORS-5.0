"""Generator yields the handle; consumer only stockpiles it."""

import pymongo


def _stream_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = pymongo.MongoClient(dsn)
    yield client


def ingest_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for client in _stream_mongo(path, host, port):
        payload = client.list_database_names()
        kept.append(client)
    return kept
