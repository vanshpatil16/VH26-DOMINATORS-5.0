"""Generator yields the handle; consumer keeps then closes it."""

import redis


def _stream_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    yield client


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    kept = None
    for client in _stream_redis_client(path, host, port):
        kept = client
        payload = client.get(key)
    kept.close()
    return payload
