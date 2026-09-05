"""Module-level registry with a shutdown that releases every entry."""

import redis


_REGISTRY = {}


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    _REGISTRY[key] = client
    payload = client.get(key)
    return payload


def shutdown():
    for client in _REGISTRY.values():
        client.close()
    _REGISTRY.clear()
