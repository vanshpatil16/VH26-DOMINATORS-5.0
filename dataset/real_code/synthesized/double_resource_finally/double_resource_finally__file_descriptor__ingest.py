"""Two independent handles, each released in its own finally."""

import os


def ingest_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = os.fdopen(fileno, "rb")
    try:
        target = os.fdopen(fileno, "rb")
        try:
            payload = source.read()
            payload = target.read()
        finally:
            target.close()
    finally:
        source.close()
    return payload
