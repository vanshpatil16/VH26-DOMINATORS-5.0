"""Load payload through contextlib.closing."""

import contextlib
import redis


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(redis.Redis(host=host)) as client:
        payload = client.get(key)
    return payload
