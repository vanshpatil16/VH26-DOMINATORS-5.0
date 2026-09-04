"""One handle per item, released in a finally."""

import redis


def ingest_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        client = redis.Redis(host=host)
        try:
            payload = client.get(key)
            collected.append(payload)
        finally:
            client.close()
    return collected
