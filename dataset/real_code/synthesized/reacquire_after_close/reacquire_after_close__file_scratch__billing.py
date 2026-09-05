"""Acquire, release, then acquire a second time and release again."""

import tempfile


def billing_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.TemporaryFile()
    try:
        handle.write(payload)
    finally:
        handle.close()
    retry = tempfile.TemporaryFile()
    try:
        retry.write(payload)
    finally:
        retry.close()
    return payload
