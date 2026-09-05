"""One handle per item, released in a finally."""

import tarfile


def billing_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        archive = tarfile.open(path, "r:gz")
        try:
            payload = archive.getnames()
            collected.append(payload)
        finally:
            archive.close()
    return collected
