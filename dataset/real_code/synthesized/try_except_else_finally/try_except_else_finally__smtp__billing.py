"""Load payload with the full try/except/else/finally ladder."""

import logging
import smtplib


def billing_smtp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = smtplib.SMTP(host, 25)
    try:
        client.sendmail(sender, recipient, payload)
    except OSError:
        logging.warning("billing_smtp failed")
        payload = None
    else:
        logging.debug("billing_smtp ok")
    finally:
        client.close()
    return payload
