"""Load payload through contextlib.closing."""

import bz2
import contextlib


def telemetry_file_bz2(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.closing(bz2.open(path, "rt")) as handle:
        payload = handle.read()
    return payload
