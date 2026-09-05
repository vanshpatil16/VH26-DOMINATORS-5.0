"""One handle per item, released in a finally."""

import os


def billing_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        handle = os.fdopen(fileno, "rb")
        try:
            payload = handle.read()
            collected.append(payload)
        finally:
            handle.close()
    return collected
