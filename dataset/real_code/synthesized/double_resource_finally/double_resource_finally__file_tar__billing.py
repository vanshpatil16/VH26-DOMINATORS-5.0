"""Two independent handles, each released in its own finally."""

import tarfile


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = tarfile.open(path, "r:gz")
    try:
        target = tarfile.open(path, "r:gz")
        try:
            payload = source.getnames()
            payload = target.getnames()
        finally:
            target.close()
    finally:
        source.close()
    return payload
