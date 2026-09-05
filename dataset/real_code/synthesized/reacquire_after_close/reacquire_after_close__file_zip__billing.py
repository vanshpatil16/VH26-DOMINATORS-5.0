"""Acquire, release, then acquire a second time and release again."""

import zipfile


def billing_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = zipfile.ZipFile(path)
    try:
        payload = archive.namelist()
    finally:
        archive.close()
    retry = zipfile.ZipFile(path)
    try:
        payload = retry.namelist()
    finally:
        retry.close()
    return payload
