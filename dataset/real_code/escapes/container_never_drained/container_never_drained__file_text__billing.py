"""Handles collected into a list nothing ever drains."""


def _collect_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        handle = open(path, encoding="utf-8")
        opened.append(handle)
    return opened


def billing_file_text(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_text(path, host, port, items=items)
    for handle in opened:
        payload = handle.read()
    return payload
