"""A plain generator whose finally releases the handle on abandon."""

import io


def billing_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    try:
        payload = handle.read(1024)
        for item in items:
            yield item
    finally:
        handle.close()
