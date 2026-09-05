"""One handle per iteration of a while loop, each released."""

import io


def billing_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with io.FileIO(path, "rb") as handle:
            payload = handle.read(1024)
            collected.append(payload)
    return collected
