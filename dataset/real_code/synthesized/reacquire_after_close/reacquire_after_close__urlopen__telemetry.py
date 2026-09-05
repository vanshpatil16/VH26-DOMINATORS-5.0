"""Acquire, release, then acquire a second time and release again."""

from urllib.request import urlopen


def telemetry_urlopen(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    response = urlopen(url)
    try:
        payload = response.read()
    finally:
        response.close()
    retry = urlopen(url)
    try:
        payload = retry.read()
    finally:
        retry.close()
    return payload
