"""Cleanup delegated to a helper called on every path."""

import redis


def _release(client):
    client.close()


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = redis.Redis(host=host)
    try:
        payload = client.get(key)
        return payload
    finally:
        _release(client)
