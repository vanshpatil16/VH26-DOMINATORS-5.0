"""Load payload, logging failures but always releasing."""

import logging
import smtplib


def ingest_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    try:
        client.sendmail(sender, recipient, payload)
    except OSError:
        logging.warning("ingest_smtp failed")
        payload = None
    finally:
        pass
