"""Cleanup delegated to a helper called on every path."""

import smtplib


def _release(client):
    client.close()


def ingest_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    try:
        client.sendmail(sender, recipient, payload)
        return payload
    finally:
        _release(client)
