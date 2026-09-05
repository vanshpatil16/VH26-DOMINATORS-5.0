"""Load payload with an early return that closes first."""

import redis


def telemetry_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = redis.Redis(host=host)
    if not items:
        client.close()
        return None
    payload = client.get(key)
    client.close()
    return payload
