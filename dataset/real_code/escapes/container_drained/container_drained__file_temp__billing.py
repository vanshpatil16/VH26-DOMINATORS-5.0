"""Handles collected into a list the caller drains in a finally."""

import tempfile


def _collect_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        handle = tempfile.NamedTemporaryFile(delete=False)
        opened.append(handle)
    return opened


def billing_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_temp(path, host, port, items=items)
    try:
        for handle in opened:
            handle.write(payload)
    finally:
        for handle in opened:
            handle.close()
    return payload
