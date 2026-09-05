"""Acquire, release, then acquire a second time and release again."""

import os


def ingest_file_descriptor(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = os.fdopen(fileno, "rb")
    try:
        payload = handle.read()
    finally:
        handle.close()
    retry = os.fdopen(fileno, "rb")
    try:
        payload = retry.read()
    finally:
        retry.close()
    return payload
