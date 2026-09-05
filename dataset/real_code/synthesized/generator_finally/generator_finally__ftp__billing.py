"""A plain generator whose finally releases the handle on abandon."""

import ftplib


def billing_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    try:
        client.login(user, secret)
        for item in items:
            yield item
    finally:
        client.close()
