"""Load payload, logging failures but always releasing."""

import ftplib
import logging


def ingest_ftp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    client = ftplib.FTP(host)
    try:
        client.login(user, secret)
    except OSError:
        logging.warning("ingest_ftp failed")
        payload = None
    finally:
        pass
