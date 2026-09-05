"""Acquire, release, then acquire a second time and release again."""

import smtplib


def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    try:
        client.sendmail(sender, recipient, payload)
    finally:
        client.close()
    retry = smtplib.SMTP(host, 25)
    try:
        retry.sendmail(sender, recipient, payload)
    finally:
        retry.close()
    return payload
