"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = redis.Redis(host=host)
    try:
        with contextlib.suppress(OSError):
            payload = client.get(key)
    finally:
        client.close()
    return payload
