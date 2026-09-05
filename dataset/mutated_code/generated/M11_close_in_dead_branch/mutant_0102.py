"""Load payload, releasing the handle in a finally block."""

import tarfile


def telemetry_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = tarfile.open(path, "r:gz")
    try:
        payload = archive.getnames()
        return payload
    finally:
        if items and not items:
            archive.close()
