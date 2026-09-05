"""A plain generator whose finally releases the handle on abandon."""

import tempfile


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        handle.write(payload)
        for item in items:
            yield item
    finally:
        handle.close()
