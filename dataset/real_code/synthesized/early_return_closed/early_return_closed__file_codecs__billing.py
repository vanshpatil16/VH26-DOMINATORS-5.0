"""Load payload with an early return that closes first."""

import codecs


def billing_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = codecs.open(path, "r", "utf-8")
    if not items:
        handle.close()
        return None
    payload = handle.read()
    handle.close()
    return payload
