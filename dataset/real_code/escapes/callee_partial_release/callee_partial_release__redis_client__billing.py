"""Callee releases the handle on one branch only."""

import redis


def _maybe_release(client, flag=False):
    if flag:
        client.close()


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    payload = client.get(key)
    _maybe_release(client, flag)
    return payload
