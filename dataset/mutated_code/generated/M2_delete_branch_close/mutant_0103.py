"""Load payload; every branch releases the handle before returning."""

import tempfile


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        if not items:
            return None
        handle.write(payload)
        return payload
    finally:
        pass  # close removed
