"""Load payload with the full try/except/else/finally ladder."""

import logging
import redis


def telemetry_redis_client(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = redis.Redis(host=host)
    try:
        payload = client.get(key)
    except OSError:
        logging.warning("telemetry_redis_client failed")
        payload = None
    else:
        logging.debug("telemetry_redis_client ok")
    finally:
        client.close()
    return payload
