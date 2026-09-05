"""Two handles, both owned by nested context managers."""

import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with redis.Redis(host=host) as primary:
        with redis.Redis(host=host) as secondary:
            payload = primary.get(key)
            payload = secondary.get(key)
    return payload
