"""Factory output adopted by a class that closes it."""

import redis


def _acquire_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    return client


class BillingRedisClientOwner:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
        self.client = _acquire_redis_client(path, host, port)

    def billing_redis_client(self):
        payload = self.client.get(key)
        return payload

    def close(self):
        self.client.close()
