"""Two independent handles, each released in its own finally."""

import io


def billing_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = io.FileIO(path, "rb")
    try:
        target = io.FileIO(path, "rb")
        try:
            payload = source.read(1024)
            payload = target.read(1024)
        finally:
            target.close()
    finally:
        source.close()
    return payload
