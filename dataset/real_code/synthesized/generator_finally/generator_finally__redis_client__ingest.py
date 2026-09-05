"""A plain generator whose finally releases the handle on abandon."""

import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = redis.Redis(host=host)
    try:
        payload = client.get(key)
        for item in items:
            yield item
    finally:
        client.close()
