"""Two independent handles, each released in its own finally."""

from urllib.request import urlopen


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = urlopen(url)
    try:
        target = urlopen(url)
        try:
            payload = source.read()
            payload = target.read()
        finally:
            target.close()
    finally:
        source.close()
    return payload
