"""Two handles, both owned by nested context managers."""

import os


def telemetry_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with os.fdopen(fileno, "rb") as primary:
        with os.fdopen(fileno, "rb") as secondary:
            payload = primary.read()
            payload = secondary.read()
    return payload
