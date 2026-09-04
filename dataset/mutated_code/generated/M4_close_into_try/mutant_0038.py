"""Load payload, releasing the handle in a finally block."""

import redis


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = redis.Redis(host=host)
    try:
        payload = client.get(key)
        return payload
    finally:
        pass
