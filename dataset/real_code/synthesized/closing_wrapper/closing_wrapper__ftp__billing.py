"""Load payload through contextlib.closing."""

import contextlib
import ftplib


def billing_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    with contextlib.closing(ftplib.FTP(host)) as client:
        client.login(user, secret)
    return payload
