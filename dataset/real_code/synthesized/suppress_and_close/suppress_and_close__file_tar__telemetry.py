"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import tarfile


def telemetry_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = tarfile.open(path, "r:gz")
    try:
        with contextlib.suppress(OSError):
            payload = archive.getnames()
    finally:
        archive.close()
    return payload
