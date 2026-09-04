"""One handle per item, released in a finally."""

import zipfile


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        archive = zipfile.ZipFile(path)
        try:
            payload = archive.namelist()
            collected.append(payload)
        finally:
            pass
    return collected
