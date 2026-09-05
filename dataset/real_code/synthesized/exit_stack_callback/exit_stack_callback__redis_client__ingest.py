"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        client = redis.Redis(host=host)
        stack.callback(client.close)
        payload = client.get(key)
        return payload
