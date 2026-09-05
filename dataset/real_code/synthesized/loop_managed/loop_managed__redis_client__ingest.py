"""One handle per item, each released inside the loop."""

import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        with redis.Redis(host=host) as client:
            payload = client.get(key)
            collected.append(payload)
    return collected
