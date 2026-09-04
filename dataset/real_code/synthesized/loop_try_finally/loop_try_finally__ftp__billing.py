"""One handle per item, released in a finally."""

import ftplib


def billing_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        client = ftplib.FTP(host)
        try:
            client.login(user, secret)
            collected.append(payload)
        finally:
            client.close()
    return collected
