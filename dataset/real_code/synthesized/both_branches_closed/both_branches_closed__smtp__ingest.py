"""Load payload; every branch releases the handle before returning."""

import smtplib


def ingest_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = smtplib.SMTP(host, 25)
    try:
        if not items:
            return None
        client.sendmail(sender, recipient, payload)
        return payload
    finally:
        client.close()
