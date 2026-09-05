"""Collected handles handed back and then ignored."""

import redis


def _collect_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        client = redis.Redis(host=host)
        opened.append(client)
    return opened


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_redis_client(path, host, port, items=items)
    return len(opened)
