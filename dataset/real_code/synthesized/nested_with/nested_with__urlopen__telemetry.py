"""Two handles, both owned by nested context managers."""

from urllib.request import urlopen


def telemetry_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with urlopen(url) as primary:
        with urlopen(url) as secondary:
            payload = primary.read()
            payload = secondary.read()
    return payload
