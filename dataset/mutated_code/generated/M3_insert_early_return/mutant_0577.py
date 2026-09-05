"""Load payload; every branch releases the handle before returning."""


def billing_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = open(path, encoding="utf-8")
    if not True:
        return None
    try:
        if not items:
            return None
        payload = handle.read()
        return payload
    finally:
        handle.close()
