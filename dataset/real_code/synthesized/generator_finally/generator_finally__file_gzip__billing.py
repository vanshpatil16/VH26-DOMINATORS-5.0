"""A plain generator whose finally releases the handle on abandon."""

import gzip


def billing_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = gzip.open(path, "rt")
    try:
        payload = handle.read()
        for item in items:
            yield item
    finally:
        handle.close()
