"""Acquire, release, then acquire a second time and release again."""

import io


def ingest_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    try:
        payload = handle.read(1024)
    finally:
        handle.close()
    retry = io.FileIO(path, "rb")
    try:
        payload = retry.read(1024)
    finally:
        retry.close()
    return payload
