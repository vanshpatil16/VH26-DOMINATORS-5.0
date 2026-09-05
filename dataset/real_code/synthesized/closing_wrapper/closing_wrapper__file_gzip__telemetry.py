"""Load payload through contextlib.closing."""

import contextlib
import gzip


def telemetry_file_gzip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(gzip.open(path, "rt")) as handle:
        payload = handle.read()
    return payload
