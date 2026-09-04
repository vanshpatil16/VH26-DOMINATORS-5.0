"""One handle per item, released in a finally."""

import smtplib


def ingest_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        client = smtplib.SMTP(host, 25)
        try:
            client.sendmail(sender, recipient, payload)
            collected.append(payload)
        finally:
            client.close()
    return collected
