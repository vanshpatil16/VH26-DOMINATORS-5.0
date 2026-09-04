"""Load payload, releasing the handle in a finally block."""

import ftplib


def billing_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = ftplib.FTP(host)
    try:
        client.login(user, secret)
        return payload
    finally:
        client.close()
