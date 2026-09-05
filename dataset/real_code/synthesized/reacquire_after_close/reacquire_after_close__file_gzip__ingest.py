"""Acquire, release, then acquire a second time and release again."""

import gzip


def ingest_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = gzip.open(path, "rt")
    try:
        payload = handle.read()
    finally:
        handle.close()
    retry = gzip.open(path, "rt")
    try:
        payload = retry.read()
    finally:
        retry.close()
    return payload
