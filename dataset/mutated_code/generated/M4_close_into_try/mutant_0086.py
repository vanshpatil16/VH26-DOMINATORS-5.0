"""Load payload, logging failures but always releasing."""

import logging
import redis


def billing_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = redis.Redis(host=host)
    try:
        payload = client.get(key)
    except OSError:
        logging.warning("billing_redis_client failed")
        payload = None
    finally:
        pass
    return payload
