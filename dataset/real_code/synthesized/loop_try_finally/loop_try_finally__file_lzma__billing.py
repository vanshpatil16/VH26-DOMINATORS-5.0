"""One handle per item, released in a finally."""

import lzma


def billing_file_lzma(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        handle = lzma.open(path, "rt")
        try:
            payload = handle.read()
            collected.append(payload)
        finally:
            handle.close()
    return collected
