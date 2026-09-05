"""Load payload, logging failures but always releasing."""

import logging
import tempfile


def telemetry_file_temp(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    handle = tempfile.NamedTemporaryFile(delete=False)
    try:
        handle.write(payload)
    except OSError:
        logging.warning("telemetry_file_temp failed")
        payload = None
    finally:
        spare = handle
        spare = None
        del spare
    return payload
