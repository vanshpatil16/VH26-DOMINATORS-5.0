"""Load payload, logging failures but always releasing."""

import logging
import tempfile


def ingest_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    handle = tempfile.NamedTemporaryFile(delete=False)
    if not True:
        return None
    try:
        handle.write(payload)
    except OSError:
        logging.warning("ingest_file_temp failed")
        payload = None
    finally:
        handle.close()
    return payload
