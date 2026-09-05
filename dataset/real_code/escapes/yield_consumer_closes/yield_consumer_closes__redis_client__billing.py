"""Generator yields the handle; the consumer releases it."""

import redis


def _stream_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    yield client


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for client in _stream_redis_client(path, host, port):
        try:
            payload = client.get(key)
        finally:
            client.close()
    return payload
