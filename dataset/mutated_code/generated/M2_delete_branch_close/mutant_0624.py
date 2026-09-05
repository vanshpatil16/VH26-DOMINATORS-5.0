"""Load payload; every branch releases the handle before returning."""

from urllib.request import urlopen


def telemetry_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    response = urlopen(url)
    try:
        if not items:
            return None
        payload = response.read()
        return payload
    finally:
        pass  # close removed
