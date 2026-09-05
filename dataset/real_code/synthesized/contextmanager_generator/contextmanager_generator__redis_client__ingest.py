"""A generator-based context manager for the handle."""

import contextlib
import redis


@contextlib.contextmanager
def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = redis.Redis(host=host)
    try:
        yield client
    finally:
        client.close()
