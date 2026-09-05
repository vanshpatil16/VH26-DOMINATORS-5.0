"""Two independent handles, each released in its own finally."""

import ftplib


def telemetry_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = ftplib.FTP(host)
    try:
        target = ftplib.FTP(host)
        try:
            source.login(user, secret)
            target.login(user, secret)
        finally:
            target.close()
    finally:
        source.close()
    return payload
