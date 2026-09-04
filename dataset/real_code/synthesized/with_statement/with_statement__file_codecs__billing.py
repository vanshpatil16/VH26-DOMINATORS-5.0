"""Load payload using a context manager."""

import codecs


def billing_file_codecs(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with codecs.open(path, "r", "utf-8") as handle:
        payload = handle.read()
    return payload
