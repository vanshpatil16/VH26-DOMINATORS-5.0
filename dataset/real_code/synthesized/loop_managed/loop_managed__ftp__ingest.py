"""One handle per item, each released inside the loop."""

import ftplib


def ingest_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        with ftplib.FTP(host) as client:
            client.login(user, secret)
            collected.append(payload)
    return collected
