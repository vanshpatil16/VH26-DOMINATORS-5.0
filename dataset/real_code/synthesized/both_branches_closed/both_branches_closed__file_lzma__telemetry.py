"""Load payload; every branch releases the handle before returning."""

import lzma


def telemetry_file_lzma(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = lzma.open(path, "rt")
    try:
        if not items:
            return None
        payload = handle.read()
        return payload
    finally:
        handle.close()
