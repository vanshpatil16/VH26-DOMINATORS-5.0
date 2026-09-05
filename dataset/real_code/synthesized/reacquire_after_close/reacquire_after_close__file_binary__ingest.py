"""Acquire, release, then acquire a second time and release again."""

import io


def ingest_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.open(path, "rb")
    try:
        payload = handle.read(4096)
    finally:
        handle.close()
    retry = io.open(path, "rb")
    try:
        payload = retry.read(4096)
    finally:
        retry.close()
    return payload
