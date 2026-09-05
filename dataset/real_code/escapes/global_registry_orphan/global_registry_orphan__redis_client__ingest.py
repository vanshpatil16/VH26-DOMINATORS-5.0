"""Module-level registry nothing ever shuts down."""

import redis


_REGISTRY = {}


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    _REGISTRY[key] = client
    payload = client.get(key)
    return payload


def lookup(key=None):
    return _REGISTRY.get(key)
