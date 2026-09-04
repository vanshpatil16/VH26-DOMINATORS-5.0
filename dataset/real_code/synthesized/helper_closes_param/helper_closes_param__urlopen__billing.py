"""Cleanup delegated to a helper called on every path."""

from urllib.request import urlopen


def _release(response):
    response.close()


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    response = urlopen(url)
    try:
        payload = response.read()
        return payload
    finally:
        _release(response)
