"""Generator yields the handle; the consumer walks away from it."""

import redis


def _stream_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    yield client


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    for client in _stream_redis_client(path, host, port):
        payload = client.get(key)
        break
    return payload
