"""Two independent handles, each released in its own finally."""

import smtplib


def telemetry_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = smtplib.SMTP(host, 25)
    try:
        target = smtplib.SMTP(host, 25)
        try:
            source.sendmail(sender, recipient, payload)
            target.sendmail(sender, recipient, payload)
        finally:
            target.close()
    finally:
        source.close()
    return payload
