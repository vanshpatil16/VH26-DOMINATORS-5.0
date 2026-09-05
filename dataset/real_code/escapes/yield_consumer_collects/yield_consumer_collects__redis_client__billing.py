"""Generator yields the handle; consumer only stockpiles it."""

import redis


def _stream_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    yield client


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = []
    for client in _stream_redis_client(path, host, port):
        payload = client.get(key)
        kept.append(client)
    return kept
