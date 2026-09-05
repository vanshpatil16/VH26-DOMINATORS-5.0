"""Factory return registered on an ExitStack by the caller."""

import contextlib
import redis


def _acquire_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    client = redis.Redis(host=host)
    return client


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        client = stack.enter_context(
            contextlib.closing(_acquire_redis_client(path, host, port)))
        payload = client.get(key)
        return payload
