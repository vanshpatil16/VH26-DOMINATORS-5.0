"""Two independent handles, each released in its own finally."""

import tempfile


def telemetry_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = tempfile.TemporaryFile()
    try:
        target = tempfile.TemporaryFile()
        try:
            source.write(payload)
            target.write(payload)
        finally:
            target.close()
    finally:
        source.close()
    return payload
