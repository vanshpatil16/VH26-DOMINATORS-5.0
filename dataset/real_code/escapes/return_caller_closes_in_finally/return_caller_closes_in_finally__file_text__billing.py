"""Factory return released by the caller in a finally."""


def _acquire_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    return handle


def billing_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = _acquire_file_text(path, host, port)
    try:
        payload = handle.read()
        return payload
    finally:
        handle.close()
