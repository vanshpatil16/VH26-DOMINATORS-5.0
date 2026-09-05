"""A generator-based context manager for the handle."""

import contextlib
import smtplib


@contextlib.contextmanager
def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    try:
        yield client
    finally:
        client.close()
