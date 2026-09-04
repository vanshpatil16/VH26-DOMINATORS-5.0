"""Load payload with an early return that closes first."""


def ingest_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = open(path, encoding="utf-8")
    if not items:
        handle.close()
        return None
    payload = handle.read()
    handle.close()
    return payload
