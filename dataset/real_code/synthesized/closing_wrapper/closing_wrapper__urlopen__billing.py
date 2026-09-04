"""Load payload through contextlib.closing."""

from urllib.request import urlopen
import contextlib


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(urlopen(url)) as response:
        payload = response.read()
    return payload
