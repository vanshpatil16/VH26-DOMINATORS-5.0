"""Load payload with an ExitStack owning the handle."""

import contextlib
import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.ExitStack() as stack:
        client = stack.enter_context(contextlib.closing(redis.Redis(host=host)))
        payload = client.get(key)
        return payload
