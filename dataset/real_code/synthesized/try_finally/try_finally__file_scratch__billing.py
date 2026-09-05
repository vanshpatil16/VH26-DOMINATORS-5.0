"""Load payload, releasing the handle in a finally block."""

import tempfile


def billing_file_scratch(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.TemporaryFile()
    try:
        handle.write(payload)
        return payload
    finally:
        handle.close()
