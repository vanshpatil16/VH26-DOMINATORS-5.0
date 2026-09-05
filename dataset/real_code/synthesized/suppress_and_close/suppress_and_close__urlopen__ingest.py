"""Errors suppressed around the use; cleanup still unconditional."""

from urllib.request import urlopen
import contextlib


def ingest_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    response = urlopen(url)
    try:
        with contextlib.suppress(OSError):
            payload = response.read()
    finally:
        response.close()
    return payload
