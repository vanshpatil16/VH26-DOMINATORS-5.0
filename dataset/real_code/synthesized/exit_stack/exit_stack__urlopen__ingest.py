"""Load payload with an ExitStack owning the handle."""

from urllib.request import urlopen
import contextlib


def ingest_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        response = stack.enter_context(contextlib.closing(urlopen(url)))
        payload = response.read()
        return payload
