"""An owner object that releases its handle in close()."""

import smtplib


class IngestSmtpClient:
    def __init__(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.client = smtplib.SMTP(host, 25)

    def run(self, path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
        self.client.sendmail(sender, recipient, payload)
        return payload

    def close(self):
        self.client.close()
