"""Callee releases the handle on one branch only."""

import tempfile


def _maybe_release(handle, flag=False):
    if flag:
        handle.close()


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    handle.write(payload)
    _maybe_release(handle, flag)
    return payload
