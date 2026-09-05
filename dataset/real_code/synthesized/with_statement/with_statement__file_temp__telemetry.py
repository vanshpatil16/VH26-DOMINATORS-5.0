"""Load payload using a context manager."""

import tempfile


def telemetry_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(payload)
    return payload
