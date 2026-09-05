"""Two handles, both owned by nested context managers."""

import requests


def telemetry_session(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with requests.Session() as primary:
        with requests.Session() as secondary:
            payload = primary.get(url)
            payload = secondary.get(url)
    return payload
