"""Load payload with the full try/except/else/finally ladder."""

import logging
import zipfile


def telemetry_file_zip(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    archive = zipfile.ZipFile(path)
    try:
        payload = archive.namelist()
    except OSError:
        logging.warning("telemetry_file_zip failed")
        payload = None
    else:
        logging.debug("telemetry_file_zip ok")
    finally:
        archive.close()
    return payload
