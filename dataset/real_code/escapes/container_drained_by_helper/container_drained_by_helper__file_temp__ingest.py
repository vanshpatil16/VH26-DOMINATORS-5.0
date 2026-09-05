"""Collected handles released by a named cleanup helper."""

import tempfile


def close_all(handles=()):
    for entry in handles:
        entry.close()


def _collect_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        handle = tempfile.NamedTemporaryFile(delete=False)
        opened.append(handle)
    return opened


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_temp(path, host, port, items=items)
    try:
        for handle in opened:
            handle.write(payload)
    finally:
        close_all(opened)
    return payload
