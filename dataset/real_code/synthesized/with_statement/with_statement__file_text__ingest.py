"""Load payload using a context manager."""


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with open(path, encoding="utf-8") as handle:
        payload = handle.read()
    return payload
