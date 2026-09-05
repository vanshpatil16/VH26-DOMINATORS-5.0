"""Load payload with an early return that closes first."""

import io


def telemetry_file_raw(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = io.FileIO(path, "rb")
    if not items:
        handle.close()
        return None
    payload = handle.read(1024)
    handle.close()
    return payload
