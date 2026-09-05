"""Load payload with an early return that closes first."""

import bz2


def telemetry_file_bz2(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = bz2.open(path, "rt")
    if not items:
        handle.close()
        return None
    payload = handle.read()
    handle.close()
    return payload
