"""One handle per iteration of a while loop, each released."""

import shelve


def telemetry_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with shelve.open(path) as shelf:
            payload = shelf.get(key)
            collected.append(payload)
    return collected
