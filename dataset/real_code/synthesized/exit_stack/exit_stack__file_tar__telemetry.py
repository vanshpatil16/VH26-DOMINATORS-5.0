"""Load payload with an ExitStack owning the handle."""

import contextlib
import tarfile


def telemetry_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        archive = stack.enter_context(contextlib.closing(tarfile.open(path, "r:gz")))
        payload = archive.getnames()
        return payload
