"""Callee releases the handle on one branch only."""


def _maybe_release(handle, flag=False):
    if flag:
        handle.close()


def billing_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = open(path, encoding="utf-8")
    payload = handle.read()
    _maybe_release(handle, flag)
    return payload
