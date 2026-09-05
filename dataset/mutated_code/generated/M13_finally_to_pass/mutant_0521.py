"""Load payload, logging failures but always releasing."""

import logging
import requests


def billing_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    session = requests.Session()
    try:
        payload = session.get(url)
    except OSError:
        logging.warning("billing_session failed")
        payload = None
    finally:
        pass
