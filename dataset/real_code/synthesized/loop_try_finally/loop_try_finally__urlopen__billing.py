"""One handle per item, released in a finally."""

from urllib.request import urlopen


def billing_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        response = urlopen(url)
        try:
            payload = response.read()
            collected.append(payload)
        finally:
            response.close()
    return collected
