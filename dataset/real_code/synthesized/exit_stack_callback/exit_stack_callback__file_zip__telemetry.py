"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import zipfile


def telemetry_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        payload = archive.namelist()
        return payload
