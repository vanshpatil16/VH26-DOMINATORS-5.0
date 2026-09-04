"""A plain generator whose finally releases the handle on abandon."""

import smtplib


def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    client = smtplib.SMTP(host, 25)
    try:
        client.sendmail(sender, recipient, payload)
        for item in items:
            yield item
    finally:
        client.close()
