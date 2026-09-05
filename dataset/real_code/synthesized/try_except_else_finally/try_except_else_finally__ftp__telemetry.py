"""Load payload with the full try/except/else/finally ladder."""

import ftplib
import logging


def telemetry_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    try:
        client.login(user, secret)
    except OSError:
        logging.warning("telemetry_ftp failed")
        payload = None
    else:
        logging.debug("telemetry_ftp ok")
    finally:
        client.close()
    return payload
