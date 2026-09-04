"""Cleanup delegated to a helper called on every path."""

import ftplib


def _release(client):
    client.close()


def billing_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = ftplib.FTP(host)
    try:
        client.login(user, secret)
        return payload
    finally:
        pass
