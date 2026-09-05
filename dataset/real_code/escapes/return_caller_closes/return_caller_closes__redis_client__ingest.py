"""Factory hands ownership to a caller that closes it."""

import contextlib
import redis


def _acquire_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    return client


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.closing(_acquire_redis_client(path, host, port)) as client:
        payload = client.get(key)
    return payload
