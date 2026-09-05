"""Two independent handles, each released in its own finally."""

import redis


def telemetry_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = redis.Redis(host=host)
    try:
        target = redis.Redis(host=host)
        try:
            payload = source.get(key)
            payload = target.get(key)
        finally:
            target.close()
    finally:
        source.close()
    return payload
