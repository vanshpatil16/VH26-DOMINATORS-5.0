"""Load payload, releasing the handle in a finally block."""

import shelve


def billing_file_shelf(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    shelf = shelve.open(path)
    try:
        payload = shelf.get(key)
        return payload
    finally:
        shelf.close()
