"""Errors suppressed around the use; cleanup still unconditional."""

import contextlib
import smtplib


def ingest_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    try:
        with contextlib.suppress(OSError):
            client.sendmail(sender, recipient, payload)
    finally:
        client.close()
    return payload
