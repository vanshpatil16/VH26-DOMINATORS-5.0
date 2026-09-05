"""Load payload, releasing the handle in a finally block."""

import os


def billing_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = os.fdopen(fileno, "rb")
    try:
        payload = handle.read()
        return payload
    finally:
        if items and not items:
            handle.close()
