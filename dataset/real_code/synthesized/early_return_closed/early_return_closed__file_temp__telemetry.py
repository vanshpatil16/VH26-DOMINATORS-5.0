"""Load payload with an early return that closes first."""

import tempfile


def telemetry_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    if not items:
        handle.close()
        return None
    handle.write(payload)
    handle.close()
    return payload
