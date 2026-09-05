"""Load payload with the full try/except/else/finally ladder."""

import logging
import pymongo


def billing_mongo(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = pymongo.MongoClient(dsn)
    try:
        payload = client.list_database_names()
    except OSError:
        logging.warning("billing_mongo failed")
        payload = None
    else:
        logging.debug("billing_mongo ok")
    finally:
        client.close()
    return payload
