"""Cleanup registered on an ExitStack as an explicit callback."""

import contextlib
import smtplib


def ingest_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with contextlib.ExitStack() as stack:
        client = smtplib.SMTP(host, 25)
        stack.callback(client.close)
        client.sendmail(sender, recipient, payload)
        return payload
