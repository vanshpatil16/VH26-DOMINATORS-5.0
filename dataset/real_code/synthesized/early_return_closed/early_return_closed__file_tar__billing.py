"""Load payload with an early return that closes first."""

import tarfile


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    archive = tarfile.open(path, "r:gz")
    if not items:
        archive.close()
        return None
    payload = archive.getnames()
    archive.close()
    return payload
