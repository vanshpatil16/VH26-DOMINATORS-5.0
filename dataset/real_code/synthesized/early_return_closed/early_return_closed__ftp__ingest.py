"""Load payload with an early return that closes first."""

import ftplib


def ingest_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    if not items:
        client.close()
        return None
    client.login(user, secret)
    client.close()
    return payload
