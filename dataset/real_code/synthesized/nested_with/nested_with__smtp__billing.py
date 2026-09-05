"""Two handles, both owned by nested context managers."""

import smtplib


def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    with smtplib.SMTP(host, 25) as primary:
        with smtplib.SMTP(host, 25) as secondary:
            primary.sendmail(sender, recipient, payload)
            secondary.sendmail(sender, recipient, payload)
    return payload
