"""One handle per iteration of a while loop, each released."""

from urllib.request import urlopen


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with urlopen(url) as response:
            payload = response.read()
            collected.append(payload)
    return collected
