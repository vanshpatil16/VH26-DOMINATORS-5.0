"""Load payload with an early return that closes first."""

from urllib.request import urlopen


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    response = urlopen(url)
    if not items:
        response.close()
        return None
    payload = response.read()
    response.close()
    return payload
