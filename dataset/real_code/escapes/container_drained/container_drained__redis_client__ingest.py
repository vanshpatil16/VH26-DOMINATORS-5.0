"""Handles collected into a list the caller drains in a finally."""

import redis


def _collect_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = redis.Redis(host=host)
        opened.append(client)
    return opened


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_redis_client(path, host, port, items=items)
    try:
        for client in opened:
            payload = client.get(key)
    finally:
        for client in opened:
            client.close()
    return payload
