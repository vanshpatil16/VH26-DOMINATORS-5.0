"""One handle per iteration of a while loop, each released."""

import smtplib


def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    collected = []
    remaining = list(items)
    while remaining:
        remaining.pop()
        with smtplib.SMTP(host, 25) as client:
            client.sendmail(sender, recipient, payload)
            collected.append(payload)
    return collected
