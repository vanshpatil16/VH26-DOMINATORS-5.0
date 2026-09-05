"""Load payload with an early return that closes first."""

import smtplib


def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    if not items:
        client.close()
        return None
    client.sendmail(sender, recipient, payload)
    client.close()
    return payload
