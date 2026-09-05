"""Factory return passed straight back out, still unreleased."""

import redis


def _acquire_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    return client


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = _acquire_redis_client(path, host, port)
    payload = client.get(key)
    return client
