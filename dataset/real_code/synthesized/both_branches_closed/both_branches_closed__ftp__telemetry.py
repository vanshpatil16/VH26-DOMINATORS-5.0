"""Load payload; every branch releases the handle before returning."""

import ftplib


def telemetry_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    try:
        if not items:
            return None
        client.login(user, secret)
        return payload
    finally:
        client.close()
