"""A plain generator whose finally releases the handle on abandon."""

import tarfile


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = tarfile.open(path, "r:gz")
    try:
        payload = archive.getnames()
        for item in items:
            yield item
    finally:
        archive.close()
