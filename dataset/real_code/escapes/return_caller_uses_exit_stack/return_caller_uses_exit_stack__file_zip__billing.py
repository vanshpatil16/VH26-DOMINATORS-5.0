"""Factory return registered on an ExitStack by the caller."""

import contextlib
import zipfile


def _acquire_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    archive = zipfile.ZipFile(path)
    return archive


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    with contextlib.ExitStack() as stack:
        archive = stack.enter_context(
            contextlib.closing(_acquire_file_zip(path, host, port)))
        payload = archive.namelist()
        return payload
