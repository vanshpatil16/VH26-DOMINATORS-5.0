"""Two independent handles, each released in its own finally."""

import io


def telemetry_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = io.open(path, "rb")
    try:
        target = io.open(path, "rb")
        try:
            payload = source.read(4096)
            payload = target.read(4096)
        finally:
            target.close()
    finally:
        source.close()
    return payload
