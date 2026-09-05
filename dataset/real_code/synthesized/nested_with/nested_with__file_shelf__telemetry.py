"""Two handles, both owned by nested context managers."""

import shelve


def telemetry_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with shelve.open(path) as primary:
        with shelve.open(path) as secondary:
            payload = primary.get(key)
            payload = secondary.get(key)
    return payload
