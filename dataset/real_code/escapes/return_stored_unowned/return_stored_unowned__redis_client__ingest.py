"""Factory return stored on a class that never releases it."""

import redis


def _acquire_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    return client


class IngestRedisClientHolder:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.client = _acquire_redis_client(path, host, port)

    def ingest_redis_client(self):
        payload = self.client.get(key)
        return payload
