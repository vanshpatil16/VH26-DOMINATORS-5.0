"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import ftplib


def telemetry_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    try:
        with contextlib.suppress(OSError):
            client.login(user, secret)
    finally:
        client.close()
    return payload
