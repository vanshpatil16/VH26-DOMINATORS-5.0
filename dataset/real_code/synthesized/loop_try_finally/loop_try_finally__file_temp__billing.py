"""One handle per item, released in a finally."""

import tempfile


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    for item in items:
        handle = tempfile.NamedTemporaryFile(delete=False)
        try:
            handle.write(payload)
            collected.append(payload)
        finally:
            handle.close()
    return collected
