"""Load payload with an early return that closes first."""

import pymongo


def telemetry_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = pymongo.MongoClient(dsn)
    if not items:
        client.close()
        return None
    payload = client.list_database_names()
    client.close()
    return payload
