"""Collected handles released by a named cleanup helper."""

import redis


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = redis.Redis(host=host)
        opened.append(client)
    return opened


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_redis_client(path, host, port, items=items)
    try:
        for client in opened:
            payload = client.get(key)
    finally:
        close_all(opened)
    return payload
