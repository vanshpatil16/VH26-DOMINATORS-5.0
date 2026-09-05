"""Two handles, both owned by nested context managers."""

import tempfile


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with tempfile.NamedTemporaryFile(delete=False) as primary:
        with tempfile.NamedTemporaryFile(delete=False) as secondary:
            primary.write(payload)
            secondary.write(payload)
    return payload
