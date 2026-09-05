"""Collected handles handed back and then ignored."""

import zipfile


def _collect_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = []
    for item in items:
        archive = zipfile.ZipFile(path)
        opened.append(archive)
    return opened


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, items=(), flag=False):
    opened = _collect_file_zip(path, host, port, items=items)
    return len(opened)
