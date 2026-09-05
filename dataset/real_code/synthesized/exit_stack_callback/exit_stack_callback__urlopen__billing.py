"""Cleanup registered on an ExitStack as an explicit callback."""

from urllib.request import urlopen
import contextlib


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        response = urlopen(url)
        stack.callback(response.close)
        payload = response.read()
        return payload
