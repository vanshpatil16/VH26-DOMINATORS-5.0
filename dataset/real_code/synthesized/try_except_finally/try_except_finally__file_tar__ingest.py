"""Load payload, logging failures but always releasing."""

import logging
import tarfile


def ingest_file_tar(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = tarfile.open(path, "r:gz")
    try:
        payload = archive.getnames()
    except OSError:
        logging.warning("ingest_file_tar failed")
        payload = None
    finally:
        archive.close()
    return payload
