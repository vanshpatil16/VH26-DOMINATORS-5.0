"""Two independent handles, each released in its own finally."""


def billing_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = open(path, encoding="utf-8")
    try:
        target = open(path, encoding="utf-8")
        try:
            payload = source.read()
            payload = target.read()
        finally:
            target.close()
    finally:
        source.close()
    return payload
