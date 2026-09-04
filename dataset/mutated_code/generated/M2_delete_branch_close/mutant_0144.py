"""Load payload with an early return that closes first."""

import io


def billing_file_binary(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = io.open(path, "rb")
    if not items:
        pass  # close removed
        return None
    payload = handle.read(4096)
    handle.close()
    return payload
