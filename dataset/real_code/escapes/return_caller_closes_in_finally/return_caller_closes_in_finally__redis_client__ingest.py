"""Factory return released by the caller in a finally."""

import redis


def _acquire_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    return client


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = _acquire_redis_client(path, host, port)
    try:
        payload = client.get(key)
        return payload
    finally:
        client.close()
