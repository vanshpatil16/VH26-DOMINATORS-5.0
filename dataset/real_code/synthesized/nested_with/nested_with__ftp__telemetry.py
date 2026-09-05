"""Two handles, both owned by nested context managers."""

import ftplib


def telemetry_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with ftplib.FTP(host) as primary:
        with ftplib.FTP(host) as secondary:
            primary.login(user, secret)
            secondary.login(user, secret)
    return payload
